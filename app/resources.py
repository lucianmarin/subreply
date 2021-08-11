from cgi import FieldStorage

import emoji
from django.db.models import Count, Max, Prefetch, Q
from emails import Message
from emails.template import JinjaTemplate
from falcon import status_codes
from falcon.hooks import before
from falcon.redirects import HTTPFound

from app.const import HTML, TEXT
from app.forms import get_content, get_emoji, get_name
from app.helpers import build_hash, parse_metadata, utc_timestamp, verify_hash
from app.hooks import auth_user, login_required
from app.jinja import render
from app.models import Comment, Relation, Save, User
from app.validation import (
    authentication, changing, profiling, registration, valid_content,
    valid_handle, valid_reply, valid_thread
)
from project.settings import FERNET, MAX_AGE, SMTP

Comments = Comment.objects.annotate(
    replies=Count('descendants')
).select_related('created_by')

PPFR = Prefetch('parent', Comments)
PFR = Prefetch('kids', Comments.order_by('id'))


def get_number(req):
    p = req.params.get('p', '1').strip()
    return int(p) if p.isdecimal() and int(p) else 0


def get_page(req):
    number = get_number(req)
    page = 'loader' if number > 1 else 'regular'
    return page, number


def paginate(req, qs, limit=10):
    page = get_number(req)
    index = (page - 1) * limit
    return qs[index:index + limit]


def not_found(resp, user, url):
    resp.text = render(page='404', user=user, url=url)
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
            resp.text = f.read()


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
        resp.text = render(page='about', view='about', user=req.user)


class EmojiResource:
    @before(auth_user)
    def on_get(self, req, resp):
        codes = emoji.UNICODE_EMOJI_ENGLISH.values()
        shortcodes = [c for c in codes if not c.count('_') and not c.count('-') and c.islower()]
        shortcodes = sorted(shortcodes)
        odds = [s for i, s in enumerate(shortcodes) if i % 2 == 0]
        evens = [s for i, s in enumerate(shortcodes) if i % 2 == 1]
        resp.text = render(
            page='emoji', view='emoji', user=req.user, rows=zip(evens, odds)
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
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='feed', form=form, number=number,
            user=req.user, entries=entries, errors={}
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
            entries = self.fetch_entries(req)
            resp.text = render(
                page='regular', view='feed', form=form, number=1,
                user=req.user, entries=entries, errors=errors
            )
        else:
            mentions, links, hashtags = parse_metadata(content)
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['mention'] = mentions[0].lower() if mentions else ''
            extra['at_user'] = User.objects.get(username=mentions[0].lower()) if mentions else None
            extra['agent'] = req.user_agent if req.user_agent else ''
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
        resp.text = render(
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
            resp.text = render(
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
            extra['agent'] = req.user_agent if req.user_agent else ''
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
        resp.text = render(
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
            resp.text = render(
                page='edit', view='edit',
                user=req.user, entry=entry, form=form, errors=errors,
                ancestors=ancestors
            )
        else:
            fields = [
                'content', 'edited_at', 'hashtag', 'link', 'agent',
                'mention', 'at_user', 'mention_seen_at'
            ]
            previous_at_user = entry.at_user
            entry.content = content
            entry.edited_at = utc_timestamp()
            entry.hashtag = hashtags[0].lower() if hashtags else ''
            entry.link = links[0].lower() if links else ''
            entry.mention = mentions[0].lower() if mentions else ''
            entry.at_user = User.objects.get(username=mentions[0].lower()) if mentions else None
            entry.agent = req.user_agent if req.user_agent else ''
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
        entries = self.fetch_entries(req, member, tab)
        page, number = get_page(req)
        threads, replies = 0, 0
        is_following, is_followed = None, None
        if number == 1:
            threads = self.fetch_threads(member).count()
            replies = self.fetch_replies(member).count()
            is_following = Relation.objects.filter(
                created_by=req.user, to_user=member
            ).exists() if req.user else False
            is_followed = Relation.objects.filter(
                created_by=member, to_user=req.user
            ).exclude(created_by=req.user).exists() if req.user else False
        resp.text = render(
            page=page, view='profile', number=number,
            user=req.user, member=member, entries=entries,
            tab=tab, is_following=is_following, is_followed=is_followed,
            threads=threads, replies=replies
        )


class FollowingResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).order_by('-id').select_related('to_user')
        return paginate(req, entries, 20)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='following', number=number,
            user=req.user, entries=entries
        )


class FollowersResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(
            to_user=req.user
        ).exclude(created_by=req.user).order_by('-id').select_related('created_by')
        return paginate(req, entries, 20)

    def clear_followers(self, user):
        Relation.objects.filter(
            to_user=user, seen_at=.0
        ).update(seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='followers', number=number,
            user=req.user, entries=entries
        )
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsResource:
    def fetch_entries(self, req):
        entries = Comments.filter(
            at_user=req.user
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries, 15)

    def clear_mentions(self, user):
        Comment.objects.filter(
            at_user=user, mention_seen_at=.0
        ).update(mention_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='mentions', number=number,
            user=req.user, entries=entries
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
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='replies', number=number,
            user=req.user, entries=entries
        )
        if req.user.notif_replies:
            self.clear_replies(req.user)


class ReplyingResource:
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
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='replying', number=number,
            user=req.user, entries=entries
        )


class SavesResource:
    def fetch_entries(self, req):
        saved_ids = Save.objects.filter(
            created_by=req.user
        ).values('to_comment__id')
        entries = Comments.filter(
            id__in=saved_ids
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries, 15)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='saves', number=number,
            user=req.user, entries=entries
        )


class LobbyResource:
    @before(auth_user)
    def on_get_apv(self, req, resp, username):
        if not req.user.id == 1:
            raise HTTPFound(f'/{username}')
        User.objects.filter(username=username.lower()).update(is_approved=True)
        raise HTTPFound(f'/{username}')

    @before(auth_user)
    def on_get_dst(self, req, resp, username):
        if not req.user.id == 1:
            raise HTTPFound(f'/{username}')
        User.objects.filter(username=username.lower()).delete()
        raise HTTPFound('/lobby')

    @before(auth_user)
    def on_get(self, req, resp):
        entries = User.objects.filter(is_approved=False).order_by('-id')
        resp.text = render(
            page='regular', view='lobby', user=req.user, entries=entries
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

    def fetch_entries(self, req, terms):
        q = self.build_query(terms)
        entries = User.objects.filter(q).exclude(
            is_approved=False
        ).order_by('-seen_at')
        return paginate(req, entries, 20)

    @before(auth_user)
    def on_get(self, req, resp):
        q = req.params.get('q', '').strip()
        terms = [t.strip() for t in q.split() if t.strip()]
        entries = self.fetch_entries(req, terms)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='people', number=number,
            q=q, placeholder="Find people",
            user=req.user, entries=entries
        )


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
        return paginate(req, entries, 15)

    @before(auth_user)
    def on_get(self, req, resp):
        q = req.params.get('q', '').strip()
        terms = [t.strip() for t in q.split() if t.strip()]
        entries = self.fetch_entries(req, terms)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='discover', number=number,
            q=q, placeholder="Search content",
            user=req.user, entries=entries
        )


class TrendingResource:
    sample = 19

    def fetch_entries(self, req):
        sampling = Comment.objects.filter(parent=None).annotate(
            replies=Count('kids')
        ).exclude(replies=0).order_by('-id').values('id')[:self.sample]
        entries = Comments.filter(
            id__in=sampling
        ).order_by('-replies', '-id').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='trending', number=number,
            user=req.user, entries=entries
        )


class AccountResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.text = render(
            page='account', view='account', user=req.user, form=form,
            change_errors={}, delete_errors={}
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
            resp.text = render(
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
            resp.text = render(
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
        resp.text = render(
            page='social', view='social', user=req.user, form=form, errors={}
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
            resp.text = render(
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
        resp.text = render(
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
            resp.text = render(
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
        resp.text = render(page='login', view='login', errors={}, form=form)

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        username = form.getvalue('username', '').strip().lower()
        password = form.getvalue('password', '')
        errors, user = authentication(username, password)
        if errors:
            resp.text = render(
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
        resp.text = render(
            page='register', view='register',
            errors={}, form=form, fields={}
        )

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        f['username'] = form.getvalue('username', '').strip().lower()
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['password1'] = form.getvalue('password1', '')
        f['password2'] = form.getvalue('password2', '')
        f['email'] = form.getvalue('email', '').strip().lower()
        errors = registration(f)
        if errors:
            resp.text = render(
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
                    'joined_at': utc_timestamp(),
                    'seen_at': utc_timestamp()
                }
            )
            # create self relation
            Relation.objects.get_or_create(
                created_at=utc_timestamp(), seen_at=utc_timestamp(),
                created_by=user, to_user=user
            )
            # subreply = User.objects.get(username='subreply')
            # Relation.objects.get_or_create(
            #     created_at=utc_timestamp(), seen_at=utc_timestamp(),
            #     created_by=user, to_user=subreply
            # )
            # clear emoji statuses for unseen people
            # half_year = utc_timestamp() - (3600 * 24 * 183)
            # User.objects.filter(seen_at__lt=half_year).update(emoji='')
            # set id cookie
            token = FERNET.encrypt(str(user.id).encode()).decode()
            resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class UnlockResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.text = render(
            page='unlock', view='unlock', errors={}, form=form
        )

    def on_get_lnk(self, req, resp, token):
        email = FERNET.decrypt(token.encode()).decode()
        user = User.objects.filter(email=email).first()
        token = FERNET.encrypt(str(user.id).encode()).decode()
        resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
        raise HTTPFound('/feed')

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        email = form.getvalue('email', '').strip().lower()
        errors = {}
        user = User.objects.filter(email=email).first()
        if not user:
            errors['email'] = "Email doesn't exist"
        if errors:
            resp.text = render(
                page='unlock', view='unlock', errors=errors, form=form
            )
        else:
            # generate token
            token = FERNET.encrypt(str(user.email).encode()).decode()
            # compose email
            m = Message(
                html=JinjaTemplate(HTML),
                text=JinjaTemplate(TEXT),
                subject="Unlock account on Subreply",
                mail_from=("Subreply", "subreply@outlook.com")
            )
            # send email
            response = m.send(
                render={"username": user, "token": token}, to=user.email, smtp=SMTP
            )
            # fallback
            if response.status_code == 250:
                raise HTTPFound('/login')
            else:
                raise HTTPFound('/unlock')
