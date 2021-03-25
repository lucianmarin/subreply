import hashlib
from cgi import FieldStorage

from django.db.models import Count, Max, Prefetch, Q
from emails import Message
from emails.template import JinjaTemplate
import emoji
from falcon import status_codes
from falcon.hooks import before
from falcon.redirects import HTTPFound

from app.const import HTML, TEXT
from app.filters import timeago
from app.forms import get_content, get_emoji, get_name
from app.helpers import build_hash, parse_metadata, utc_timestamp, verify_hash
from app.hooks import auth_user, login_required
from app.jinja import render
from app.models import Comment, Relation, Reset, Save, User
from app.validation import (
    authentication, changing, profiling, registration, valid_content,
    valid_handle, valid_password, valid_reply, valid_thread
)
from project.settings import DEBUG, FERNET, MAX_AGE, SMTP

Comments = Comment.objects.annotate(
    replies=Count('descendants')
).select_related('created_by')

PPFR = Prefetch('parent', Comments)
PFR = Prefetch('kids', Comments.order_by('id'))


def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    page = int(p) if p.isdecimal() and int(p) else 0
    backward, forward, query, pages = 0, 0, [], {}
    if page:
        index = (page - 1) * limit
        query = qs[index:index + limit + 1]
        if len(query):
            backward = page - 1
        if len(query) == limit + 1:
            forward = page + 1
    if backward or forward:
        pages = {'previous': backward, 'current': page, 'next': forward}
    return query[:limit], pages


def not_found(resp, user, url):
    resp.body = render(page='404', user=user, url=url)
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
            raise HTTPFound('/discover')


class AboutResource:
    @before(auth_user)
    def on_get(self, req, resp):
        resp.body = render(page='about', view='about', user=req.user)


class EmojiResource:
    @before(auth_user)
    def on_get(self, req, resp):
        codes = emoji.UNICODE_EMOJI_ENGLISH.values()
        shortcodes = [c for c in codes if c.count('_') < 2]
        shortcodes = sorted(shortcodes, key=str.casefold)
        resp.body = render(
            page='emoji', view='emoji', user=req.user, shortcodes=shortcodes
        )


class FeedResource:
    def fetch_entries(self, req):
        friends = Relation.objects.filter(created_by=req.user).values('to_user_id')
        entries = Comments.filter(
            created_by__in=friends, parent=None
        ).order_by('-id').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        entries, pages = self.fetch_entries(req)
        resp.body = render(
            page='feed', view='feed', form=form,
            user=req.user, entries=entries, pages=pages, errors={}
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
            resp.body = render(
                page='feed', view='feed', form=form,
                user=req.user, entries=entries, pages=pages, errors=errors
            )
        else:
            mentions, links, hashtags = parse_metadata(content)
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['mention'] = mentions[0].lower() if mentions else ''
            extra['at_user'] = User.objects.get(username=mentions[0].lower()) if mentions else None
            th, is_new = Comment.objects.get_or_create(
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            raise HTTPFound('/')


class ReplyResource:
    def fetch_entries(self, parent):
        return Comments.filter(parent=parent).order_by('-id').prefetch_related(PFR)

    def fetch_ancestors(self, parent):
        return Comments.filter(id__in=parent.ancestors.values('id')).order_by('id')

    @before(auth_user)
    def on_get(self, req, resp, username, base):
        parent = Comments.filter(id=int(base, 36)).first()
        if not parent or parent.created_by.username != username.lower():
            return not_found(resp, req.user, f'/{username}/{base}')
        duplicate = Comment.objects.filter(
            parent=parent, created_by=req.user
        ).exists() if req.user else True
        ancestors = self.fetch_ancestors(parent)
        entries = self.fetch_entries(parent)
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='reply', view='reply',
            user=req.user, entry=parent, form=form, errors={}, entries=entries,
            ancestors=ancestors, duplicate=duplicate
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, username, base):
        parent = Comments.filter(
            id=int(base, 36)
        ).select_related('parent').first()
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
            resp.body = render(
                page='reply', view='reply',
                user=req.user, entry=parent, form=form, errors=errors,
                entries=entries, ancestors=ancestors, duplicate=False
            )
        else:
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['mention'] = mentions[0].lower() if mentions else ''
            extra['at_user'] = User.objects.get(username=mentions[0].lower()) if mentions else None
            re, is_new = Comment.objects.get_or_create(
                parent=parent,
                to_user=parent.created_by,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            re.set_ancestors()
            raise HTTPFound(f'/{username}/{base}')


class EditResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, base):
        entry = Comments.filter(
            id=int(base, 36)
        ).prefetch_related(PPFR).first()
        if not entry or entry.created_by != req.user or entry.replies:
            return not_found(resp, req.user, f'/edit/{base}')
        ancestors = [entry.parent] if entry.parent_id else []
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='edit', view='edit',
            user=req.user, entry=entry, form=form, errors={},
            ancestors=ancestors
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, base):
        entry = Comments.filter(
            id=int(base, 36)
        ).prefetch_related(PPFR).first()
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
            resp.body = render(
                page='edit', view='edit',
                user=req.user, entry=entry, form=form, errors=errors,
                ancestors=ancestors
            )
        else:
            fields = [
                'content', 'edited_at', 'hashtag', 'link',
                'mention', 'at_user', 'mention_seen_at'
            ]
            previous_at_user = entry.at_user
            entry.content = content
            entry.edited_at = utc_timestamp()
            entry.hashtag = hashtags[0].lower() if hashtags else ''
            entry.link = links[0].lower() if links else ''
            entry.mention = mentions[0].lower() if mentions else ''
            entry.at_user = User.objects.get(username=mentions[0].lower()) if mentions else None
            if previous_at_user != entry.at_user:
                entry.mention_seen_at = .0
            entry.save(update_fields=fields)
            raise HTTPFound(f'/{entry.created_by}/{base}')


class ProfileResource:
    def fetch_threads(self, user):
        return Comments.filter(
            created_by=user, parent=None
        ).order_by('-id').select_related('created_by').prefetch_related(PFR)

    def fetch_replies(self, user):
        return Comments.filter(
            created_by=user
        ).exclude(parent=None).order_by('-id').prefetch_related(PPFR)

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
        resp.body = render(
            page='profile', view='profile',
            user=req.user, member=member, entries=entries, pages=pages,
            tab=tab, is_following=is_following, is_followed=is_followed,
            threads=threads, replies=replies
        )


class FollowingResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).order_by('-id').select_related('to_user')
        return paginate(req, entries, 32)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        following = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).count()
        followers = Relation.objects.filter(
            to_user=req.user
        ).exclude(created_by=req.user).count()
        resp.body = render(
            page='regular', view='following', following=following,
            followers=followers, user=req.user, entries=entries, pages=pages
        )


class FollowersResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(
            to_user=req.user
        ).exclude(created_by=req.user).order_by('-id').select_related('created_by')
        return paginate(req, entries, 32)

    def clear_followers(self, user):
        Relation.objects.filter(
            to_user=user, seen_at=.0
        ).update(seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        following = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).count()
        followers = Relation.objects.filter(
            to_user=req.user
        ).exclude(created_by=req.user).count()
        resp.body = render(
            page='regular', view='followers', following=following,
            followers=followers, user=req.user, entries=entries, pages=pages
        )
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsResource:
    def fetch_entries(self, req):
        entries = Comments.filter(
            at_user=req.user
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries, 24)

    def clear_mentions(self, user):
        Comment.objects.filter(
            at_user=user, mention_seen_at=.0
        ).update(mention_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        mentions = Comment.objects.filter(at_user=req.user).count()
        resp.body = render(
            page='regular', view='mentions', mentions=mentions,
            user=req.user, entries=entries, pages=pages
        )
        if req.user.notif_mentions:
            self.clear_mentions(req.user)


class RepliesResource:
    def fetch_entries(self, req):
        entries = Comments.filter(
            to_user=req.user
        ).order_by('-id').prefetch_related(PPFR)
        return paginate(req, entries)

    def clear_replies(self, user):
        Comment.objects.filter(
            to_user=user, reply_seen_at=.0
        ).update(reply_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        replies = Comment.objects.filter(to_user=req.user).count()
        resp.body = render(
            page='regular', view='replies', replies=replies,
            user=req.user, entries=entries, pages=pages
        )
        if req.user.notif_replies:
            self.clear_replies(req.user)


class ReplyingResource:
    def get_count(self, req):
        friends = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).values('to_user_id')
        return Comments.filter(
            created_by__in=friends
        ).exclude(parent=None).exclude(
            to_user=req.user
        ).count()

    def fetch_entries(self, req):
        friends = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).values('to_user_id')
        entries = Comments.filter(
            created_by__in=friends
        ).exclude(parent=None).exclude(
            to_user=req.user
        ).order_by('-id').prefetch_related(PPFR)
        return paginate(req, entries)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        replying = self.get_count(req)
        resp.body = render(
            page='regular', view='replying', replying=replying,
            user=req.user, entries=entries, pages=pages
        )


class SavesResource:
    def fetch_entries(self, req):
        saved_ids = Save.objects.filter(
            created_by=req.user
        ).values('to_comment__id')
        entries = Comments.filter(
            id__in=saved_ids
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries, 24)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, pages = self.fetch_entries(req)
        saves = Save.objects.filter(created_by=req.user).count()
        resp.body = render(
            page='regular', view='saves', saves=saves,
            user=req.user, entries=entries, pages=pages
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
        sort = '-seen_at' if kind == 'seen' else '-id'
        entries = User.objects.filter(q).order_by(sort)
        return paginate(req, entries, 32)

    def get_people(self, req, resp, kind):
        q = req.params.get('q', '').strip()
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, pages = self.fetch_entries(req, terms, kind)
        resp.body = render(
            page='regular', view='people', placeholder="Find people",
            user=req.user, entries=entries, pages=pages, q=q, kind=kind
        )

    @before(auth_user)
    def on_get_seen(self, req, resp):
        self.get_people(req, resp, 'seen')

    @before(auth_user)
    def on_get_joined(self, req, resp):
        self.get_people(req, resp, 'joined')


class DiscoverResource:
    def build_query(self, terms):
        query = Q()
        for term in terms:
            query &= Q(content__icontains=term)
        return query

    def fetch_entries(self, req, terms):
        if terms:
            sq = self.build_query(terms)
        else:
            last_ids = User.objects.annotate(lid=Max('comments')).values('lid')
            sq = Q(id__in=last_ids)
        entries = Comments.filter(sq).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries, 24)

    @before(auth_user)
    def on_get(self, req, resp):
        q = req.params.get('q', '').strip()
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, pages = self.fetch_entries(req, terms)
        resp.body = render(
            page='regular', view='discover', placeholder="Search content",
            user=req.user, entries=entries, pages=pages, q=q
        )


class TrendingResource:
    def fetch_entries(self, req, sample):
        sampling = Comment.objects.filter(parent=None).annotate(
            replies=Count('kids')
        ).exclude(replies=0).order_by('-id').values('id')[:sample]
        entries = Comments.filter(
            id__in=sampling
        ).order_by('-replies', '-id').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp, sample):
        entries, pages = self.fetch_entries(req, sample)
        resp.body = render(
            page='regular', view='trending', sample=sample,
            user=req.user, entries=entries, pages=pages
        )

    def on_get_s(self, req, resp):
        self.on_get(req, resp, 16)

    def on_get_m(self, req, resp):
        self.on_get(req, resp, 32)

    def on_get_l(self, req, resp):
        self.on_get(req, resp, 64)


class ActionResource:
    def follow(self, user, member):
        Relation.objects.get_or_create(
            created_at=utc_timestamp(), created_by=user, to_user=member
        )

    def unfollow(self, user, member):
        Relation.objects.filter(created_by=user, to_user=member).delete()

    def destroy(self, user, member):
        if user.id == 1:
            member.delete()

    def on_get_flw(self, req, resp, username):
        self.get_action(req, resp, username, 'follow')

    def on_get_unf(self, req, resp, username):
        self.get_action(req, resp, username, 'unfollow')

    def on_get_dst(self, req, resp, username):
        self.get_action(req, resp, username, 'destroy')

    @before(auth_user)
    @before(login_required)
    def get_action(self, req, resp, username, action):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            return not_found(resp, req.user, f'/{username}')
        if req.user and member.id != req.user.id:
            fn = getattr(self, action)
            fn(req.user, member)
        raise HTTPFound(f'/{username}')


class AccountResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='account', view='account', user=req.user, form=form
        )

    @before(auth_user)
    @before(login_required)
    def on_post_chg(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        current = form.getvalue('current', '')
        password1 = form.getvalue('password1', '')
        password2 = form.getvalue('password2', '')
        errors = changing(req.user, current, password1, password2)
        if errors:
            resp.body = render(
                page='account', view='account',
                user=req.user, change_errors=errors, form=form
            )
        else:
            req.user.password = build_hash(password1)
            req.user.save()
            resp.unset_cookie('identity')
            raise HTTPFound('/login')

    @before(auth_user)
    @before(login_required)
    def on_post_del(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        current = form.getvalue('current', '')
        errors = {}
        if not verify_hash(current, req.user.password):
            errors['current'] = "Password doesn't match"
        if errors:
            resp.body = render(
                page='account', view='account',
                user=req.user, delete_errors=errors, form=form
            )
        else:
            req.user.delete()
            resp.unset_cookie('identity')
            raise HTTPFound('/discover')


class SocialResource:
    sites = [
        'dribbble', 'github', 'instagram', 'linkedin',
        'pinterest', 'soundcloud', 'telegram', 'twitter'
    ]

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='social', view='social', user=req.user, form=form
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        for site in self.sites:
            value = form.getvalue(site, '').strip().lower()
            if value:
                f[site] = value
        errors = {}
        for field, value in f.items():
            if valid_handle(value):
                errors[field] = valid_handle(value)
        if errors:
            resp.body = render(
                page='social', view='social',
                user=req.user, errors=errors, form=form, fields=f
            )
        else:
            req.user.links = f
            req.user.save(update_fields=['links'])
            raise HTTPFound('/{0}'.format(req.user))


class OptionsResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='options', view='options',
            user=req.user, errors={}, form=form
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        f['username'] = form.getvalue('username', '').strip().lower()
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['email'] = form.getvalue('email', '').strip().lower()
        f['bio'] = get_content(form, 'bio')
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.getvalue('birthday', '').strip()
        f['location'] = form.getvalue('location', '')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = profiling(f, req.user.id)
        if errors:
            resp.body = render(
                page='options', view='options',
                user=req.user, errors=errors, form=form, fields=f
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
        resp.body = render(page='login', view='login', errors={}, form=form)

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        username = form.getvalue('username', '').strip().lower()
        password = form.getvalue('password', '')
        errors, user = authentication(username, password)
        if errors:
            resp.body = render(
                page='login', view='login', errors=errors, form=form
            )
        else:
            token = FERNET.encrypt(str(user.id).encode())
            resp.set_cookie('identity', token.decode(), path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class LogoutResource:
    def on_get(self, req, resp):
        resp.unset_cookie('identity')
        raise HTTPFound('/discover')


class RegisterResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='register', view='register',
            errors={}, form=form, fields={}
        )

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        user_agent = req.headers.get('USER-AGENT', '').strip()
        f['user_agent'] = user_agent if user_agent else 'empty'
        f['remote_addr'] = '127.0.0.5' if DEBUG else req.access_route[0]
        f['username'] = form.getvalue('username', '').strip().lower()
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['password1'] = form.getvalue('password1', '')
        f['password2'] = form.getvalue('password2', '')
        f['email'] = form.getvalue('email', '').strip().lower()
        f['bio'] = get_content(form, 'bio')
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.getvalue('birthday', '').strip()
        f['location'] = form.getvalue('location', '')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = registration(f)
        if errors:
            resp.body = render(
                page='register', view='register',
                errors=errors, form=form, fields=f
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
            token = FERNET.encrypt(str(user.id).encode())
            resp.set_cookie('identity', token.decode(), path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class ResetResource:
    hours = 8

    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='reset', view='reset', errors={}, form=form
        )

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        email = form.getvalue('email', '').strip().lower()
        # clean up
        hours_ago = utc_timestamp() - self.hours * 3600
        Reset.objects.filter(created_at__lt=hours_ago).delete()
        errors = {}
        user = User.objects.filter(email=email).first()
        if not user:
            errors['email'] = "Email doesn't exist"
        else:
            reset = Reset.objects.filter(email=user.email).first()
            if reset:
                remains = reset.created_at + self.hours * 3600 - utc_timestamp()
                errors['email'] = f"Try again in {timeago(remains)}, reset already sent"
        if errors:
            resp.body = render(
                page='reset', view='reset', errors=errors, form=form
            )
        else:
            # generate code
            unique = str(utc_timestamp()).encode()
            code = hashlib.shake_128(unique).hexdigest(3)
            # compose email
            m = Message(
                html=JinjaTemplate(HTML),
                text=JinjaTemplate(TEXT),
                subject="Reset password",
                mail_from=("Subreply", "subreply@outlook.com")
            )
            # send email
            response = m.send(
                render={"username": user, "code": code}, to=user.email, smtp=SMTP
            )
            # create reset entry
            if response.status_code == 250:
                Reset.objects.update_or_create(
                    created_at=utc_timestamp(), email=user.email, code=code
                )
                raise HTTPFound('/change')
            else:
                raise HTTPFound('/reset')


class ChangeResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.body = render(
            page='change', view='change', errors={}, form=form
        )

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        code = form.getvalue('code', '').strip().lower()
        email = form.getvalue('email', '').strip().lower()
        password1 = form.getvalue('password1', '')
        password2 = form.getvalue('password2', '')
        errors = {}
        reset = Reset.objects.filter(email=email, code=code).first()
        if not reset:
            errors['email'] = "Email didn't receive this code"
        errors['password'] = valid_password(password1, password2)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            resp.body = render(
                page='change', view='change', errors=errors, form=form
            )
        else:
            user = User.objects.filter(email=email).first()
            user.password = build_hash(password1)
            user.save(update_fields=['password'])
            token = FERNET.encrypt(str(user.id).encode())
            resp.set_cookie(
                'identity', token.decode(), path="/", max_age=MAX_AGE
            )
            reset.delete()
            raise HTTPFound('/feed')
