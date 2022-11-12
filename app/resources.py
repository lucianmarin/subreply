from cgi import FieldStorage

from django.db.models import Count, Max, Prefetch, Q
from emails import Message
from emails.template import JinjaTemplate
from emoji import demojize, get_emoji_unicode_dict
from falcon import HTTPFound, HTTPNotFound, before
from falcon.status_codes import HTTP_200
from strictyaml import as_document

from app.forms import get_content, get_emoji, get_name
from app.helpers import build_hash, parse_metadata, utc_timestamp, verify_hash
from app.hooks import auth_user, login_required
from app.jinja import render
from app.models import Article, Comment, Relation, Save, User
from app.validation import (
    authentication, profiling, registration, valid_content, valid_handle,
    valid_password, valid_reply, valid_thread
)
from project.settings import FERNET, MAX_AGE, SMTP
from project.vars import UNLOCK_HTML, UNLOCK_TEXT

Comments = Comment.objects.annotate(
    replies=Count('descendants')
).select_related('created_by')

PPFR = Prefetch('parent', Comments)
PFR = Prefetch('kids', Comments.order_by('id'))
RPFR = Prefetch('kids', Comments.prefetch_related(PFR))


def get_number(req):
    p = req.params.get('p', '1').strip()
    return int(p) if p.isdecimal() and int(p) else 0


def get_page(req):
    number = get_number(req)
    page = 'loader' if number > 1 else 'regular'
    return page, number


def paginate(req, qs, limit=16):
    page = get_number(req)
    index = (page - 1) * limit
    return qs[index:index + limit]


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

    def on_get(self, req, resp, filename):  # noqa
        print("load", filename)
        name, ext = filename.split('.')
        mode = 'rb' if ext in self.binary else 'r'
        resp.status = HTTP_200
        resp.content_type = self.mime_types[ext]
        resp.cache_control = ["max-age=3600000"]
        with open(f'static/{filename}', mode) as f:
            resp.text = f.read()


class MainResource:
    @before(auth_user)
    def on_get(self, req, resp):  # noqa
        if req.user:
            raise HTTPFound('/feed')
        else:
            raise HTTPFound('/trending')


class AboutResource:
    @before(auth_user)
    def on_get(self, req, resp):
        luc = User.objects.get(id=1)
        sub = User.objects.get(id=2)
        emo = User.objects.exclude(
            id__in=[1, 2]
        ).exclude(emoji="").order_by("?").first()
        resp.text = render(
            page='about', view='about', user=req.user, luc=luc, sub=sub, emo=emo
        )


class EmojiResource:
    @before(auth_user)
    def on_get(self, req, resp):
        codes = get_emoji_unicode_dict('en').keys()
        shortcodes = set()
        for c in codes:
            if c.count('_') < 2 and '-' not in c and '’' not in c and c.islower():
                shortcodes.add(c)
        shortcodes = sorted(shortcodes)
        odds = [s for i, s in enumerate(shortcodes) if i % 2 == 0]
        evens = [s for i, s in enumerate(shortcodes) if i % 2 == 1]
        resp.text = render(
            page='emoji', view='emoji', user=req.user, rows=zip(evens, odds)
        )


class TxtResource:
    def on_get_bots(self, req, resp):
        lines = (
            "User-agent: *",
            "Disallow: /news/*",
            "Disallow: /read/*",
            "",
            "Sitemap: https://subreply.com/sitemap.txt"
        )
        resp.text = "\n".join(lines)

    def on_get_map(self, req, resp):
        threads = Comment.objects.filter(parent=None).exclude(kids=None).values_list(
            'created_by__username', 'id'
        ).order_by('id')
        users = User.objects.exclude(comments=None).values_list('username')
        thr_urls = [f"https://subreply.com/{u}/{id}" for u, id in threads]
        usr_urls = [f"https://subreply.com/{u}" for u, in users]
        urls = sorted(thr_urls + usr_urls)
        resp.text = "\n".join(urls)


class RedirectResource:
    @before(auth_user)
    def on_get(self, req, resp, id):
        reply = Comment.objects.filter(id=id).first()
        if reply:
            raise HTTPFound(f"/{reply.created_by}/{reply.id}")
        raise HTTPNotFound


class FeedResource:
    def fetch_entries(self, req):
        friends = Relation.objects.filter(created_by=req.user).values('to_user_id')
        entries = Comments.filter(
            created_by__in=friends
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        s = req.params.get('s', '').strip()
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='feed', number=number, content=s,
            user=req.user, entries=entries, errors={}
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        if not content:
            raise HTTPFound("/feed")
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            entries = self.fetch_entries(req)
            resp.text = render(
                page='regular', view='feed', content=content, number=1,
                user=req.user, entries=entries, errors=errors
            )
        else:
            hashtags, links, mentions = parse_metadata(content)
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['at_user'] = User.objects.get(
                username=mentions[0].lower()
            ) if mentions else None
            th, is_new = Comment.objects.get_or_create(
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            raise HTTPFound('/feed')


class ReplyResource:
    def fetch_entries(self, parent):
        return Comments.filter(parent=parent).order_by('-id').prefetch_related(RPFR)

    def fetch_ancestors(self, parent):
        return Comments.filter(id__in=parent.ancestors.values('id')).order_by('id')

    @before(auth_user)
    def on_get(self, req, resp, username, id):
        parent = Comments.filter(id=id).first()
        if not parent or parent.created_by.username != username.lower():
            raise HTTPNotFound
        duplicate = Comment.objects.filter(
            parent=parent, created_by=req.user
        ).exists() if req.user else True
        ancestors = self.fetch_ancestors(parent)
        entries = self.fetch_entries(parent)
        resp.text = render(
            page='reply', view='reply', content='',
            user=req.user, entry=parent, errors={}, entries=entries,
            ancestors=ancestors, duplicate=duplicate
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, username, id):
        parent = Comments.filter(id=id).select_related('parent').first()
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        if not content:
            raise HTTPFound(f"/{req.user}/{id}")
        hashtags, links, mentions = parse_metadata(content)
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
                user=req.user, entry=parent, content=content, errors=errors,
                entries=entries, ancestors=ancestors, duplicate=False
            )
        else:
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['at_user'] = User.objects.get(
                username=mentions[0].lower()
            ) if mentions else None
            re, is_new = Comment.objects.get_or_create(
                parent=parent,
                to_user=parent.created_by,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            re.set_ancestors()
            raise HTTPFound(f"/{req.user}/{re.id}")


class EditResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, id):
        entry = Comments.filter(id=id).prefetch_related(PPFR).first()
        if not entry or entry.created_by != req.user or entry.replies:
            raise HTTPNotFound
        ancestors = [entry.parent] if entry.parent_id else []
        resp.text = render(
            page='edit', view='edit',
            user=req.user, entry=entry, content=entry.content, errors={},
            ancestors=ancestors
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, id):
        entry = Comments.filter(id=id).prefetch_related(PPFR).first()
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        hashtags, links, mentions = parse_metadata(content)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            if entry.parent_id:
                errors['content'] = valid_reply(
                    entry.parent, req.user, content, mentions
                )
            else:
                errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            ancestors = [entry.parent] if entry.parent_id else []
            resp.text = render(
                page='edit', view='edit',
                user=req.user, entry=entry, content=content, errors=errors,
                ancestors=ancestors
            )
        else:
            fields = ['content', 'edited_at', 'hashtag', 'link',
                      'at_user', 'mention_seen_at']
            previous_at_user = entry.at_user
            entry.content = content
            entry.edited_at = utc_timestamp()
            entry.hashtag = hashtags[0].lower() if hashtags else ''
            entry.link = links[0].lower() if links else ''
            entry.at_user = User.objects.get(
                username=mentions[0].lower()
            ) if mentions else None
            if previous_at_user != entry.at_user:
                entry.mention_seen_at = .0
            entry.save(update_fields=fields)
            raise HTTPFound(f"/{req.user}/{entry.id}")


class ProfileResource:
    def fetch_entries(self, req, member):
        entries = Comments.filter(
            created_by=member
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        entries = self.fetch_entries(req, member)
        page, number = get_page(req)
        is_following, is_followed = None, None
        if number == 1:
            is_following = Relation.objects.filter(
                created_by=req.user, to_user=member
            ).exists() if req.user else False
            is_followed = Relation.objects.filter(
                created_by=member, to_user=req.user
            ).exclude(created_by=req.user).exists() if req.user else False
        resp.text = render(
            page=page, view='profile', number=number, errors={},
            user=req.user, member=member, entries=entries,
            is_following=is_following, is_followed=is_followed
        )


class FollowingResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(
            created_by=req.user
        ).exclude(to_user=req.user).order_by('-id').select_related('to_user')
        return paginate(req, entries, 24)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='following', number=number, user=req.user,
            entries=entries, limit=24
        )


class FollowersResource:
    def fetch_entries(self, req):
        entries = Relation.objects.filter(
            to_user=req.user
        ).exclude(created_by=req.user).order_by('-id').select_related('created_by')
        return paginate(req, entries, 24)

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
            page=page, view='followers', number=number, user=req.user,
            entries=entries, limit=24
        )
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsResource:
    def fetch_entries(self, req):
        entries = Comments.filter(
            at_user=req.user
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries)

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


class SavedResource:
    def fetch_entries(self, req):
        saved_ids = Save.objects.filter(created_by=req.user).values('to_comment__id')
        entries = Comments.filter(
            id__in=saved_ids
        ).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='saved', number=number, user=req.user,
            entries=entries
        )


class LobbyResource:
    @before(auth_user)
    def on_get_approve(self, req, resp, username):  # noqa
        if not req.user.id == 1:
            raise HTTPFound(f'/{username}')
        User.objects.filter(username=username.lower()).update(is_approved=True)
        raise HTTPFound(f'/{username}')

    @before(auth_user)
    def on_get_destroy(self, req, resp, username):  # noqa
        if not req.user.id == 1:
            raise HTTPFound(f'/{username}')
        User.objects.filter(username=username.lower()).delete()
        raise HTTPFound('/lobby')

    def fetch_entries(self, req):
        entries = User.objects.filter(is_approved=False).order_by('-id')
        return paginate(req, entries, 24)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='lobby', number=number, user=req.user,
            entries=entries, limit=24
        )


class PeopleResource:
    fields = [
        "username", "first_name", "last_name", "email",
        "description", "birthday", "location", "emoji", "website"
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
        return paginate(req, entries, 24)

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries = self.fetch_entries(req, terms)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='people', number=number, q=q,
            placeholder="Find people", user=req.user,
            entries=entries, limit=24
        )


class DiscoverResource:
    def build_query(self, terms):
        query = Q()
        for term in terms:
            query &= Q(content__icontains=term)
        return query

    def fetch_entries(self, req, terms):
        if terms:
            f = self.build_query(terms)
            entries = Comments.filter(f).order_by('-id').prefetch_related(PFR, PPFR)
        else:
            lastest = User.objects.annotate(last_id=Max('comments__id')).values('last_id')
            entries = Comments.filter(id__in=lastest).order_by('-id').prefetch_related(PFR, PPFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries = self.fetch_entries(req, terms)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='discover', number=number,
            q=q, placeholder="Search content",
            user=req.user, entries=entries
        )


class TrendingResource:
    def fetch_entries(self, req, sample):
        sampling = Comment.objects.filter(parent=None).exclude(
            kids=None
        ).order_by('-id').values('id')[:sample]
        entries = Comments.filter(
            id__in=sampling
        ).order_by('-replies', '-id').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req, sample=20)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='trending', number=number,
            user=req.user, entries=entries
        )


class LinksResource:
    def fetch_entries(self, req):
        entries = Comments.exclude(link='').order_by('-id').prefetch_related(PFR)
        return paginate(req, entries)

    @before(auth_user)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req)
        page, number = get_page(req)
        resp.text = render(
            page=page, view='links', number=number,
            user=req.user, entries=entries
        )


class NewsResource:
    def fetch_news(self, req):
        user_id = req.user.id if req.user else 0
        latest_ids = Article.objects.exclude(ids__contains=user_id).order_by(
            'domain', '-pub_at'
        ).distinct('domain').values('id')
        entries = Article.objects.filter(
            id__in=latest_ids
        ).order_by('-pub_at')
        return paginate(req, entries)

    def fetch_read(self, req):
        entries = Article.objects.exclude(readers=0).order_by('-readers', '-pub_at')
        return paginate(req, entries)

    def get_count(self, user, is_read):
        entries = Article.objects.all()
        if is_read:
            return entries.filter(readers=0).count()
        return entries.exclude(readers=0).count()

    @before(auth_user)
    def on_get_news(self, req, resp):
        entries = self.fetch_news(req)
        page, number = get_page(req)
        # read = self.get_count(req.user, is_read=False)
        resp.text = render(
            page=page, view='news', number=number, user=req.user,
            entries=entries
        )

    @before(auth_user)
    def on_get_read(self, req, resp):
        entries = self.fetch_read(req)
        page, number = get_page(req)
        # read = self.get_count(req.user, is_read=True)
        resp.text = render(
            page=page, view='read', number=number, user=req.user,
            entries=entries
        )


class ArticleResource:
    @before(auth_user)
    def on_get_linker(self, req, resp, id):
        article = Article.objects.filter(id=id).first()
        if not article:
            raise HTTPNotFound
        if req.user and req.user.is_approved:
            article.increment(req.user.id)
        raise HTTPFound(article.url)

    @before(auth_user)
    def on_get_reader(self, req, resp, id):
        article = Article.objects.filter(id=id).first()
        if not article:
            raise HTTPNotFound
        if req.user and req.user.is_approved:
            article.increment(req.user.id)
        resp.text = render(
            page='reader', view='reader', user=req.user, entry=article
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
    def on_post_change(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        password1 = form.getvalue('password1', '')
        password2 = form.getvalue('password2', '')
        errors = {}
        errors['password'] = valid_password(password1, password2)
        errors = {k: v for k, v in errors.items() if v}
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
    def on_post_export(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        username = form.getvalue('username', '').strip().lower()
        errors = {}
        if req.user.username != username:
            errors['username'] = "Username doesn't match"
        if errors:
            resp.text = render(
                page='account', view='account',
                user=req.user, delete_errors=errors, form=form
            )
        else:
            comments = Comment.objects.filter(
                created_by=req.user
            ).order_by('-id').prefetch_related('parent__created_by')
            data = []
            for comment in comments:
                d = {}
                if comment.parent:
                    p = {}
                    p['username'] = comment.parent.created_by.username
                    p['content'] = comment.parent.content
                    d['parent'] = p
                d['content'] = comment.content
                d['created'] = comment.created_at
                if comment.edited_at:
                    d['edited'] = comment.edited_at
                data.append(d)
            resp.content_type = "application/x-yaml"
            resp.downloadable_as = f"subreply-{username}.yaml"
            resp.text = as_document(data).as_yaml()

    @before(auth_user)
    @before(login_required)
    def on_post_delete(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        confirm = form.getvalue('confirm', '')
        errors = {}
        if not verify_hash(confirm, req.user.password):
            errors['confirm'] = "Password doesn't match"
        if errors:
            resp.text = render(
                page='account', view='account',
                user=req.user, delete_errors=errors, form=form
            )
        else:
            req.user.delete()
            resp.unset_cookie('identity')
            raise HTTPFound('/trending')


class SocialResource:
    sites = [
        'dribbble', 'github', 'instagram', 'linkedin', 'patreon',
        'paypal', 'soundcloud', 'spotify', 'telegram', 'twitter'
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
            raise HTTPFound(f"/{req.user.username}")


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
        f['email'] = form.getvalue('email', '').strip().lower()
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.getvalue('birthday', '').strip()
        f['location'] = form.getvalue('location', '')
        f['description'] = get_content(form, 'description')
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
    def on_get(self, req, resp):  # noqa
        resp.unset_cookie('identity')
        raise HTTPFound('/trending')


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
        f['email'] = form.getvalue('email', '').strip().lower()
        f['password1'] = form.getvalue('password1', '')
        f['password2'] = form.getvalue('password2', '')
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.getvalue('birthday', '').strip()
        f['location'] = form.getvalue('location', '')
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
                    'joined_at': utc_timestamp(),
                    'seen_at': utc_timestamp(),
                    'password': build_hash(f['password1']),
                    'email': f['email'],
                    'first_name': f['first_name'],
                    'last_name': f['last_name'],
                    'emoji': f['emoji'],
                    'birthday': f['birthday'],
                    'location': f['location'],
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
            token = FERNET.encrypt(str(user.id).encode()).decode()
            resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class UnlockResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.text = render(
            page='unlock', view='unlock', errors={}, form=form
        )

    def on_get_link(self, req, resp, token):  # noqa
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
                html=JinjaTemplate(UNLOCK_HTML),
                text=JinjaTemplate(UNLOCK_TEXT),
                subject="Unlock account on Subreply",
                mail_from=("Subreply", "subreply@outlook.com")
            )
            # send email
            response = m.send(
                render={"username": user, "token": token},
                to=user.email,
                smtp=SMTP
            )
            # fallback
            if response.status_code == 250:
                raise HTTPFound('/login')
            else:
                raise HTTPFound('/unlock')
