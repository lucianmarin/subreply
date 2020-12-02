import hashlib
from cgi import FieldStorage

from django.db.models import Max, Prefetch, Q
from emails import Message
from emails.template import JinjaTemplate as Tpl
from falcon import status_codes
from falcon.hooks import before
from falcon.redirects import HTTPFound
from project.settings import DEBUG, MAX_AGE, SMTP, F

from app.const import COUNTRIES
from app.forms import get_content, get_emoji
from app.helpers import build_hash, parse_metadata, utc_timestamp
from app.hooks import auth_user, login_required
from app.jinja import env
from app.models import Comment, Relation, Reset, Save, User
from app.validation import (authentication, changing, profiling, registration,
                            valid_content, valid_password, valid_reply,
                            valid_thread)

PFR = Prefetch('kids', queryset=Comment.objects.order_by('id').select_related('created_by'))


def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    page = int(p) if p.isdecimal() and int(p) else 1
    bottom = (page - 1) * limit
    top = bottom + limit + 1
    query = qs[bottom:top]
    if not len(query):
        query = qs[:limit + 1]
        page = 1
        bottom = 0
    pages = {
        'prev': page - 1,
        'this': page,
        'next': page + 1 if len(query) == limit + 1 else 0,
    }
    if not bottom and len(query) < limit + 1:
        pages = {}
    return query[:limit], pages


def not_found(resp, user, url):
    template = env.get_template('pages/404.html')
    resp.body = template.render(user=user, url=url)
    resp.status = status_codes.HTTP_404


class StaticResource:
    binary = ['png', 'jpg', 'woff', 'woff2']
    mime_types = {
        'js': "application/javascript",
        'json': "application/json",
        'css': "text/css",
        'woff': "font/woff",
        'woff2': "font/woff2",
        'png': "image/png",
        'jpg': "image/jpeg"
    }

    def on_get(self, req, resp, filename):
        print("load", filename)
        name, ext = filename.split('.')
        mode = 'rb' if ext in self.binary else 'r'
        resp.status = status_codes.HTTP_200
        resp.content_type = self.mime_types[ext]
        resp.cache_control = ["max-age=3600000"]
        with open(f'static/{filename}', mode) as f:
            resp.body = f.read()


class MainResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        else:
            raise HTTPFound('/trending')


class AboutResource:
    @before(auth_user)
    def on_get(self, req, resp):
        template = env.get_template('pages/about.html')
        resp.body = template.render(user=req.user, view='about')


class FeedResource:
    def fetch_entries(self, req):
        friends = Relation.objects.filter(created_by=req.user).values('to_user_id')
        entries = Comment.objects.filter(created_by__in=friends, parent=None).order_by('-id').select_related('created_by').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/feed.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, errors={},
            form=form, view='feed'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            entries, pages = self.fetch_entries(req)
            template = env.get_template('pages/feed.html')
            resp.body = template.render(
                user=req.user, entries=entries, pages=pages, errors=errors,
                form=form, view='feed'
            )
        else:
            mentions, links, hashtags = parse_metadata(content)
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['mention'] = mentions[0].lower() if mentions else ''
            extra['mentioned'] = User.objects.get(username=mentions[0].lower()) if mentions else None
            th, is_new = Comment.objects.get_or_create(
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            if th.mentioned:
                th.mentioned.up_mentions()
            raise HTTPFound('/')


class ReplyResource:
    def fetch_entries(self, parent):
        return Comment.objects.filter(parent=parent).order_by('-id').select_related('created_by').prefetch_related(PFR)

    def fetch_ancestors(self, parent):
        return Comment.objects.filter(id__in=parent.ancestors).order_by('id').select_related('created_by', 'parent')

    @before(auth_user)
    def on_get(self, req, resp, username, base):
        parent = Comment.objects.filter(
            id=int(base, 36)
        ).select_related('created_by', 'parent').first()
        if not parent or parent.created_by.username != username.lower():
            return not_found(resp, req.user, f'/{username}/{base}')
        duplicate = Comment.objects.filter(
            parent=parent, created_by=req.user
        ).exists() if req.user else True
        ancestors = self.fetch_ancestors(parent)
        entries = self.fetch_entries(parent)
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/reply.html')
        resp.body = template.render(
            user=req.user, entry=parent, form=form, errors={}, entries=entries,
            ancestors=ancestors, duplicate=duplicate, view='reply'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, username, base):
        parent = Comment.objects.filter(
            id=int(base, 36)
        ).select_related('created_by', 'parent').first()
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        mentions, links, hashtags = parse_metadata(content)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            errors['content'] = valid_reply(parent, req.user, content, mentions)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            ancestors = self.fetch_ancestors(parent)
            entries = self.fetch_entries(parent)
            template = env.get_template('pages/reply.html')
            resp.body = template.render(
                user=req.user, entry=parent, form=form, errors=errors,
                entries=entries, ancestors=ancestors, duplicate=False,
                view='reply'
            )
        else:
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['mention'] = mentions[0].lower() if mentions else ''
            extra['mentioned'] = User.objects.get(username=mentions[0].lower()) if mentions else None
            re, is_new = Comment.objects.get_or_create(
                parent=parent,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            if re.mentioned:
                re.mentioned.up_mentions()
            re.up_ancestors()
            re.add_replies()
            parent.created_by.up_replies()
            raise HTTPFound(f'/{username}/{base}')


class EditResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, base):
        entry = Comment.objects.filter(
            id=int(base, 36)
        ).select_related('created_by', 'parent').first()
        if not entry or entry.created_by != req.user or entry.replies:
            return not_found(resp, req.user, f'/edit/{base}')
        ancestors = [entry.parent] if entry.parent_id else []
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/edit.html')
        resp.body = template.render(
            user=req.user, entry=entry, form=form, errors={},
            ancestors=ancestors, view='edit'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, base):
        entry = Comment.objects.filter(
            id=int(base, 36)
        ).select_related('created_by', 'parent').first()
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        mentions, links, hashtags = parse_metadata(content)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            if entry.parent_id:
                errors['content'] = valid_reply(entry.parent, req.user, content, mentions)
            else:
                errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            ancestors = [entry.parent] if entry.parent_id else []
            template = env.get_template('pages/edit.html')
            resp.body = template.render(
                user=req.user, entry=entry, form=form, errors=errors,
                ancestors=ancestors, view='edit'
            )
        else:
            fields = [
                'content', 'edited_at', 'hashtag', 'link',
                'mention', 'mentioned', 'mention_seen_at'
            ]
            previously_mentioned = entry.mentioned
            entry.content = content
            entry.edited_at = utc_timestamp()
            entry.hashtag = hashtags[0].lower() if hashtags else ''
            entry.link = links[0].lower() if links else ''
            entry.mention = mentions[0].lower() if mentions else ''
            entry.mentioned = User.objects.get(username=mentions[0].lower()) if mentions else None
            if previously_mentioned != entry.mentioned:
                entry.mention_seen_at = .0
            entry.save(update_fields=fields)
            if previously_mentioned:
                previously_mentioned.up_mentions()
            if entry.mentioned:
                entry.mentioned.up_mentions()
            raise HTTPFound(f'/{entry.created_by}/{base}')


class ProfileResource:
    def fetch_threads(self, user):
        return Comment.objects.filter(created_by=user, parent=None).order_by('-id').select_related('created_by').prefetch_related(PFR)

    def fetch_replies(self, user):
        return Comment.objects.filter(created_by=user).exclude(parent=None).order_by('-id').select_related('created_by', 'parent__created_by', 'parent__parent')

    def fetch_entries(self, req, member, tab):
        method = getattr(self, f'fetch_{tab}')
        return paginate(req, method(member))

    @before(auth_user)
    def on_get_re(self, req, resp, username):
        self.get_profile(req, resp, username, 'replies')

    @before(auth_user)
    def on_get_th(self, req, resp, username):
        self.get_profile(req, resp, username, 'threads')

    def get_profile(self, req, resp, username, tab):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            return not_found(resp, req.user, f'/{username}')
        entries, pages = self.fetch_entries(req, member, tab)
        threads = self.fetch_threads(member).count()
        replies = self.fetch_replies(member).count()
        is_following = Relation.objects.filter(
            created_by=req.user, to_user=member
        ).exists() if req.user else False
        is_followed = Relation.objects.filter(
            created_by=member, to_user=req.user
        ).exclude(created_by=req.user).exists() if req.user else False
        template = env.get_template('pages/profile.html')
        resp.body = template.render(
            user=req.user, member=member, entries=entries, pages=pages,
            tab=tab, is_following=is_following, is_followed=is_followed,
            threads=threads, replies=replies, view='profile'
        )


class FollowingResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(created_by=req.user).exclude(to_user=req.user).order_by('-id').select_related('to_user')
        return paginate(req, entries, 32)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, view='following'
        )


class FollowersResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(to_user=req.user).exclude(created_by=req.user).order_by('-id').select_related('created_by')
        return paginate(req, entries, 32)

    def clear_followers(self, user):
        Relation.objects.filter(
            to_user=user, seen_at=.0
        ).update(seen_at=utc_timestamp())
        user.up_followers()

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, view='followers'
        )
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsResource:
    def fetch_entries(self, req):
        entries = Comment.objects.filter(mentioned=req.user).order_by('-id').order_by('-id').select_related('created_by', 'parent')
        return paginate(req, entries, 24)

    def clear_mentions(self, user):
        Comment.objects.filter(
            mentioned=user, mention_seen_at=.0
        ).update(mention_seen_at=utc_timestamp())
        user.up_mentions()

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, view='mentions'
        )
        if req.user.notif_mentions:
            self.clear_mentions(req.user)


class RepliesResource:
    def fetch_entries(self, req):
        entries = Comment.objects.filter(parent__created_by=req.user).order_by('-id').select_related('created_by', 'parent__created_by', 'parent__parent')
        return paginate(req, entries)

    def clear_replies(self, user):
        Comment.objects.filter(
            parent__created_by=user, reply_seen_at=.0
        ).update(reply_seen_at=utc_timestamp())
        user.up_replies()

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, view='replies'
        )
        if req.user.notif_replies:
            self.clear_replies(req.user)


class ReplyingResource:
    def fetch_entries(self, req):
        friends = Relation.objects.filter(created_by=req.user).exclude(to_user=req.user).values('to_user_id')
        entries = Comment.objects.filter(created_by__in=friends).exclude(parent=None).exclude(parent__created_by=req.user).order_by('-id').select_related('created_by', 'parent__created_by', 'parent__parent')
        return paginate(req, entries)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, view='replying'
        )


class SavedResource:
    def fetch_entries(self, req):
        entries = Save.objects.filter(created_by=req.user).order_by('-id').select_related('to_comment__created_by', 'to_comment__parent')
        return paginate(req, entries, 24)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, view='saved'
        )


class PeopleResource:
    fields = [
        "username", "first_name", "last_name", "email",
        "bio", "birthday", "location", "emoji", "website"
    ]

    def build_query(self, terms):
        query = Q()
        for term in terms:
            subquery = Q()
            for field in self.fields:
                icontains = {f'{field}__icontains': term}
                subquery |= Q(**icontains)
            query &= subquery
        return query

    def fetch_entries(self, req, terms, kind):
        q = self.build_query(terms)
        order_by = '-seen_at' if kind == 'seen' else '-id'
        entries = User.objects.filter(q).order_by(order_by)
        return paginate(req, entries, 32)

    def get_people(self, req, resp, kind):
        q = req.params.get('q', '').strip()
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, pages = self.fetch_entries(req, terms, kind)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, q=q, kind=kind,
            view='people', placeholder="Find people"
        )

    @before(auth_user)
    def on_get(self, req, resp):
        self.get_people(req, resp, 'seen')

    @before(auth_user)
    def on_get_joined(self, req, resp):
        self.get_people(req, resp, 'joined')


class DiscoverResource:
    kinds = {'anything': None, 'replies': False, 'threads': True}

    def build_query(self, terms):
        query = Q()
        for term in terms:
            query &= Q(content__icontains=term)
        return query

    def fetch_entries(self, req, terms, is_thread):
        max_id = Max('comments__id')
        sq = Q()
        if is_thread is not None:
            sq = Q(parent__isnull=is_thread)
            max_id = Max('comments__id', filter=Q(comments__parent__isnull=is_thread))
        last_ids = User.objects.annotate(last_id=max_id).values('last_id')
        q = self.build_query(terms) & sq if terms else Q(id__in=last_ids)
        entries = Comment.objects.filter(q).order_by('-id').select_related('created_by').prefetch_related('parent')
        return paginate(req, entries, 24)

    def get_discover(self, req, resp, kind):
        is_thread = self.kinds[kind]
        q = req.params.get('q', '').strip()
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, pages = self.fetch_entries(req, terms, is_thread)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages, q=q,
            kind=kind, view='discover', placeholder=f"Search {kind}"
        )

    @before(auth_user)
    def on_get(self, req, resp):
        self.get_discover(req, resp, 'anything')

    @before(auth_user)
    def on_get_re(self, req, resp):
        self.get_discover(req, resp, 'replies')

    @before(auth_user)
    def on_get_th(self, req, resp):
        self.get_discover(req, resp, 'threads')


class TrendingResource:
    def fetch_entries(self, req, sample):
        sampling = Comment.objects.filter(parent=None).exclude(replies=0).order_by('-id').values('id')[:sample]
        entries = Comment.objects.filter(id__in=sampling).order_by('-replies', '-id').select_related('created_by').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp, sample):
        sample = int(sample) if sample.isdecimal() and int(sample) else 16
        entries, pages = self.fetch_entries(req, sample)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=entries, pages=pages,
            sample=sample, view='trending'
        )

    def on_get_default(self, req, resp):
        self.on_get(req, resp, '16')


class ActionResource:
    def follow(self, user, member):
        Relation.objects.get_or_create(
            created_at=utc_timestamp(), created_by=user, to_user=member
        )
        member.up_followers()

    def unfollow(self, user, member):
        Relation.objects.filter(created_by=user, to_user=member).delete()
        member.up_followers()

    @before(auth_user)
    @before(login_required)
    def on_get_f(self, req, resp, username):
        self.get_action(req, resp, username, 'follow')

    @before(auth_user)
    @before(login_required)
    def on_get_unf(self, req, resp, username):
        self.get_action(req, resp, username, 'unfollow')

    def get_action(self, req, resp, username, action):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            return not_found(resp, req.user, f'/{username}')
        if req.user and member.id != req.user.id:
            fn = getattr(self, action)
            fn(req.user, member)
        raise HTTPFound(f'/{username}')


class PasswordResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/password.html')
        resp.body = template.render(
            user=req.user, errors={}, form=form, view='password'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        current = form.getvalue('current', '')
        password1 = form.getvalue('password1', '')
        password2 = form.getvalue('password2', '')
        errors = changing(req.user, current, password1, password2)
        if errors:
            template = env.get_template('pages/password.html')
            resp.body = template.render(
                user=req.user, errors=errors, form=form, view='password'
            )
        else:
            req.user.password = build_hash(password1)
            req.user.save()
            resp.unset_cookie('identity')
            raise HTTPFound('/login')


class SettingsResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/settings.html')
        resp.body = template.render(
            user=req.user, errors={}, form=form,
            countries=COUNTRIES, view='settings'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        f['username'] = form.getvalue('username', '').strip().lower()
        fn_parts = form.getvalue('first_name', '').split()
        f['first_name'] = "".join([p.strip() for p in fn_parts]).capitalize()
        ln_parts = form.getvalue('last_name', '').split()
        f['last_name'] = "".join([p.strip() for p in ln_parts]).capitalize()
        f['email'] = form.getvalue('email', '').strip().lower()
        bio_parts = form.getvalue('bio', '').split()
        f['bio'] = " ".join([p.strip() for p in bio_parts])
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.getvalue('birthday', '').strip()
        f['location'] = form.getvalue('location', '')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = profiling(f, req.user.id)
        if errors:
            template = env.get_template('pages/settings.html')
            resp.body = template.render(
                user=req.user, errors=errors, form=form, fields=f,
                countries=COUNTRIES, view='settings'
            )
        else:
            for field, value in f.items():
                if getattr(req.user, field, '') != value:
                    setattr(req.user, field, value)
            req.user.save()
            raise HTTPFound('/{0}'.format(req.user))


class LoginResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/login.html')
        resp.body = template.render(errors={}, form=form, view='login')

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        username = form.getvalue('username', '').strip().lower()
        password = form.getvalue('password', '')
        errors, user = authentication(username, password)
        if errors:
            template = env.get_template('pages/login.html')
            resp.body = template.render(errors=errors, form=form, view='login')
        else:
            token = F.encrypt(str(user.id).encode())
            resp.set_cookie('identity', token.decode(), path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class LogoutResource:
    def on_get(self, req, resp):
        resp.unset_cookie('identity')
        raise HTTPFound('/trending')


class RegisterResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/register.html')
        resp.body = template.render(
            countries=COUNTRIES, errors={}, form=form, fields={},
            view='register'
        )

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        user_agent = req.headers.get('USER-AGENT', '').strip()
        f['user_agent'] = user_agent if user_agent else 'empty'
        f['remote_addr'] = '127.0.0.5' if DEBUG else req.access_route[0]
        f['username'] = form.getvalue('username', '').strip().lower()
        fn_parts = form.getvalue('first_name', '').split()
        f['first_name'] = "".join([p.strip() for p in fn_parts]).capitalize()
        ln_parts = form.getvalue('last_name', '').split()
        f['last_name'] = "".join([p.strip() for p in ln_parts]).capitalize()
        f['password1'] = form.getvalue('password1', '')
        f['password2'] = form.getvalue('password2', '')
        f['email'] = form.getvalue('email', '').strip().lower()
        bio_parts = form.getvalue('bio', '').split()
        f['bio'] = " ".join([p.strip() for p in bio_parts])
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.getvalue('birthday', '').strip()
        f['location'] = form.getvalue('location', '')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = registration(f)
        if errors:
            template = env.get_template('pages/register.html')
            resp.body = template.render(
                countries=COUNTRIES, errors=errors, form=form, fields=f,
                view='register'
            )
        else:
            user, is_new = User.objects.get_or_create(
                username=f['username'],
                defaults={
                    'first_name': f['first_name'],
                    'last_name': f['last_name'],
                    'password': build_hash(f['password1']),
                    'email': f['email'],
                    'bio': f['bio'],
                    'birthday': f['birthday'],
                    'location': f['location'],
                    'emoji': f['emoji'],
                    'website': f['website'],
                    'joined_at': utc_timestamp(),
                    'seen_at': utc_timestamp(),
                    'remote_addr': f['remote_addr']
                }
            )
            # create self relation
            Relation.objects.get_or_create(
                created_at=utc_timestamp(), seen_at=utc_timestamp(),
                created_by=user, to_user=user
            )
            # clear emoji statuses for unseen people
            # half_year = utc_timestamp() - (3600 * 24 * 183)
            # User.objects.filter(seen_at__lt=half_year).update(emoji='')
            # set id cookie
            token = F.encrypt(str(user.id).encode())
            resp.set_cookie('identity', token.decode(), path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class ResetResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/reset.html')
        resp.body = template.render(errors={}, form=form, view='reset')

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        email = form.getvalue('email', '').strip().lower()
        # clean up
        one_day_ago = utc_timestamp() - 24 * 3600
        Reset.objects.filter(created_at__lt=one_day_ago).delete()
        errors = {}
        user = User.objects.filter(email=email).first()
        if not user:
            errors['username'] = "Email doesn't exist"
        else:
            reset = Reset.objects.filter(
                email=user.email, created_at__gt=one_day_ago
            ).exists()
            if reset:
                errors['reset'] = "Reset already exists"
        if errors:
            template = env.get_template('pages/reset.html')
            resp.body = template.render(errors=errors, form=form, view='reset')
        else:
            # generate code
            plain = "{0}-{1}".format(utc_timestamp(), user.email)
            code = hashlib.md5(plain.encode()).hexdigest()
            # compose email
            m = Message(
                html=Tpl("<html><p>Hello,</p><p>You can change your password for @{{ username }} on Subreply using the following link https://subreply.com/reset/{{ code }} and after that you will be logged in with the new credentials.</p><p>Delete this email if you didn't make such request.</p>"),
                text=Tpl("Hello,\nYou can change your password for @{{ username }} on Subreply using the following link https://subreply.com/reset/{{ code }} and after that you will be logged in with the new credentials.\nDelete this email if you didn't make such request."),
                subject=Tpl("Reset password"),
                mail_from=("Subreply", "subreply@outlook.com")
            )
            # send email
            response = m.send(
                render={"username": user, "code": code}, to=user.email, smtp=SMTP
            )
            # create reset entry
            if response.status_code == 250:
                Reset.objects.get_or_create(
                    created_at=utc_timestamp(), email=user.email, code=code
                )
                print("message sent")
            else:
                print("message not sent")
            raise HTTPFound('/login')


class ChangeResource:
    def on_get(self, req, resp, code):
        reset = Reset.objects.filter(code=code).first()
        if not reset:
            raise HTTPFound('/login')
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/change.html')
        resp.body = template.render(
            code=code, errors={}, form=form, view='change'
        )

    def on_post(self, req, resp, code):
        form = FieldStorage(fp=req.stream, environ=req.env)
        email = form.getvalue('email', '').strip().lower()
        password1 = form.getvalue('password1', '')
        password2 = form.getvalue('password2', '')
        errors = {}
        reset = Reset.objects.filter(email=email, code=code).first()
        if not reset:
            errors['email'] = "Email isn't requesting a reset"
        errors['password'] = valid_password(password1, password2)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            template = env.get_template('pages/change.html')
            resp.body = template.render(
                code=code, errors=errors, form=form, view='change'
            )
        else:
            user = User.objects.filter(email=email).first()
            user.password = build_hash(password1)
            user.save(update_fields=['password'])
            token = F.encrypt(str(user.id).encode())
            resp.set_cookie('identity', token.decode(), path="/", max_age=MAX_AGE)
            reset.delete()
            raise HTTPFound('/feed')
