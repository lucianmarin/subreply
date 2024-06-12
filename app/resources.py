from cgi import FieldStorage

from django.db.models import Count, Prefetch, Q, Max
from emails import Message
from emails.template import JinjaTemplate
from emoji import demojize, get_emoji_unicode_dict
from falcon import HTTPFound, HTTPNotFound, before
from falcon.status_codes import HTTP_200
from strictyaml import as_document

from app.forms import get_content, get_emoji, get_location, get_metadata, get_name
from app.hooks import auth_user, login_required
from app.jinja import render
from app.models import Comment, Relation, Room, Save, User
from app.utils import build_hash, utc_timestamp, verify_hash
from app.validation import (authentication, profiling, registration, valid_content,
                            valid_handle, valid_password, valid_phone, valid_reply,
                            valid_thread, valid_wallet, valid_hashtag)
from project.settings import FERNET, MAX_AGE, SMTP
from project.vars import UNLOCK_HTML, UNLOCK_TEXT

Comments = Comment.objects.annotate(
    replies=Count('descendants')
).select_related('created_by', 'in_room')

PPFR = Prefetch('parent', Comments)
PFR = Prefetch('kids', Comments.order_by('-id'))
RPFR = Prefetch('kids', Comments.prefetch_related(PFR))


def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    number = int(p) if p.isdecimal() and int(p) else 0
    page = 'loader' if number > 1 else 'regular'
    index = (number - 1) * limit
    return qs[index:index + limit], page, number


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

    @before(auth_user)
    def on_get_terms(self, req, resp):
        resp.text = render(
            page='terms', view='about', user=req.user
        )

    @before(auth_user)
    def on_get_privacy(self, req, resp):
        resp.text = render(
            page='privacy', view='about', user=req.user
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
    def on_get_bots(self, req, resp):  # noqa
        lines = (
            "User-agent: *",
            "",
            "User-agent: Google-Extended",
            "User-agent: GPTBot",
            "User-agent: PetalBot"
            "Disallow: /",
            "",
            "Sitemap: https://subreply.com/sitemap.txt"
        )
        resp.text = "\n".join(lines)

    def on_get_map(self, req, resp):  # noqa
        replies = Comments.filter(parent=None).exclude(replies=0).values_list('id').order_by('id')
        groups = Room.objects.exclude(Q(threads=None) & Q(hashtags=None)).values_list('name')
        users = User.objects.exclude(comments=None).values_list('username')
        reply_urls = [f"https://subreply.com/reply/{i}" for i, in replies]
        group_urls = [f"https://subreply.com/group/{n}" for n, in groups]
        user_urls = [f"https://subreply.com/{u}" for u, in users]
        urls = sorted(user_urls + reply_urls + group_urls)
        resp.text = "\n".join(urls)


class FeedResource:
    placeholder = "What are you up to?"

    def fetch_entries(self, user):
        friends = Relation.objects.filter(created_by=user).values('to_user_id')
        entries = Comments.filter(created_by__in=friends).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='feed', number=number, content="",
            user=req.user, entries=entries, errors={},
            placeholder=self.placeholder
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        if not content:
            raise HTTPFound('/feed')
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            entries = self.fetch_entries(req.user)[:16]
            resp.text = render(
                page='regular', view='feed', content=content, number=1,
                user=req.user, entries=entries, errors=errors,
                placeholder=self.placeholder
            )
        else:
            hashtags, links, mentions = get_metadata(content)
            extra = {}
            extra['link'] = links[0].lower() if links else ''
            extra['at_room'] = Room.objects.get_or_create(
                name=hashtags[0].lower()
            )[0] if hashtags else None
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
        return Comments.filter(
            id__in=parent.ancestors.values('id')
        ).order_by('id').prefetch_related(PPFR)

    @before(auth_user)
    def on_get(self, req, resp, id):
        parent = Comments.filter(id=id).first()
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
    def on_post(self, req, resp, id):
        parent = Comments.filter(id=id).select_related('parent').first()
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        if not content:
            raise HTTPFound(f"/reply/{id}")
        hashtags, links, mentions = get_metadata(content)
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
            extra['link'] = links[0].lower() if links else ''
            extra['at_room'] = Room.objects.get_or_create(
                name=hashtags[0].lower()
            )[0] if hashtags else None
            extra['at_user'] = User.objects.get(
                username=mentions[0].lower()
            ) if mentions else None
            re, is_new = Comment.objects.get_or_create(
                parent=parent,
                to_user=parent.created_by,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                in_room=parent.in_room,
                **extra
            )
            re.set_ancestors()
            raise HTTPFound(f"/reply/{re.id}")


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
        hashtags, links, mentions = get_metadata(content)
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
            fields = ['content', 'edited_at', 'link', 'at_room', 'at_user',
                      'mention_seen_at']
            previous_at_user = entry.at_user
            entry.content = content
            entry.edited_at = utc_timestamp()
            entry.link = links[0].lower() if links else ''
            entry.at_room = Room.objects.get_or_create(
                name=hashtags[0].lower()
            )[0] if hashtags else None
            entry.at_user = User.objects.get(
                username=mentions[0].lower()
            ) if mentions else None
            if previous_at_user != entry.at_user:
                entry.mention_seen_at = .0
            entry.save(update_fields=fields)
            raise HTTPFound(f"/reply/{entry.id}")


class GroupResource:
    placeholder = "Chat in #{0}"

    def fetch_entries(self, room):
        entries = Comments.filter(Q(in_room=room) | Q(at_room=room)).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp, name):
        room = Room.objects.filter(name=name.lower()).first()
        if not room:
            raise HTTPNotFound
        entries, page, number = paginate(req, self.fetch_entries(room))
        resp.text = render(
            page=page, view='group', number=number, content='',
            user=req.user, entries=entries, errors={}, room=room,
            placeholder=self.placeholder.format(room)
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, name):
        room = Room.objects.filter(name=name.lower()).first()
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = get_content(form)
        if not content:
            raise HTTPFound(f"/group/{name}")
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            entries = self.fetch_entries(room)[:16]
            resp.text = render(
                page='regular', view='group', number=1, content=content,
                user=req.user, entries=entries, errors=errors, room=room,
                placeholder=self.placeholder.format(room)
            )
        else:
            hashtags, links, mentions = get_metadata(content)
            extra = {}
            extra['link'] = links[0].lower() if links else ''
            extra['at_room'] = Room.objects.get_or_create(
                name=hashtags[0].lower()
            )[0] if hashtags else None
            extra['at_user'] = User.objects.get(
                username=mentions[0].lower()
            ) if mentions else None
            th, is_new = Comment.objects.get_or_create(
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                in_room=room,
                **extra
            )
            raise HTTPFound(f"/group/{name}")


class MemberResource:
    def fetch_entries(self, member):
        entries = Comments.filter(created_by=member).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        entries, page, number = paginate(req, self.fetch_entries(member))
        resp.text = render(
            page=page, view='member', number=number, errors={},
            user=req.user, member=member, entries=entries
        )


class FollowingResource:
    def fetch_entries(self, user):
        entries = Relation.objects.filter(created_by=user).exclude(to_user=user)
        return entries.order_by('-id').select_related('to_user')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user), 24)
        resp.text = render(
            page=page, view='following', number=number, user=req.user,
            entries=entries, limit=24
        )


class FollowersResource:
    def fetch_entries(self, user):
        entries = Relation.objects.filter(to_user=user).exclude(created_by=user)
        return entries.order_by('-id').select_related('created_by')

    def clear_followers(self, user):
        Relation.objects.filter(
            to_user=user, seen_at=.0
        ).update(seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user), 24)
        resp.text = render(
            page=page, view='followers', number=number, user=req.user,
            entries=entries, limit=24
        )
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsResource:
    def fetch_entries(self, user):
        entries = Comments.filter(at_user=user).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    def clear_mentions(self, user):
        Comment.objects.filter(
            at_user=user, mention_seen_at=.0
        ).update(mention_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='mentions', number=number, user=req.user, entries=entries
        )
        if req.user.notif_mentions:
            self.clear_mentions(req.user)


class RepliesResource:
    def fetch_entries(self, user):
        entries = Comments.filter(to_user=user).order_by('-id')
        return entries.prefetch_related(PPFR)

    def clear_replies(self, user):
        Comment.objects.filter(
            to_user=user, reply_seen_at=.0
        ).update(reply_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='replies', number=number, user=req.user, entries=entries
        )
        if req.user.notif_replies:
            self.clear_replies(req.user)


class SavesResource:
    def fetch_entries(self, user):
        saved_ids = Save.objects.filter(created_by=user).values('to_comment__id')
        entries = Comments.filter(id__in=saved_ids).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='saves', number=number, user=req.user, entries=entries
        )


class IncomersResource:
    def fetch_incomers(self):
        return User.objects.filter(is_approved=False).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_incomers())
        resp.text = render(
            page=page, view='incomers', number=number, user=req.user, entries=entries
        )

    @before(auth_user)
    def on_get_approve(self, req, resp, username):  # noqa
        if not req.user.id == 1:
            raise HTTPFound('/incomers')
        User.objects.filter(username=username.lower()).update(is_approved=True)
        raise HTTPFound('/incomers')

    @before(auth_user)
    def on_get_destroy(self, req, resp):  # noqa
        if not req.user.id == 1:
            raise HTTPFound('/incomers')
        User.objects.filter(is_approved=False).delete()
        raise HTTPFound('/incomers')


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

    def fetch_entries(self, terms):
        q = self.build_query(terms)
        qs = User.objects.filter(q).exclude(is_approved=False)
        return qs.order_by('id') if terms else qs.order_by('-id')

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries = self.fetch_entries(terms)
        entries, page, number = paginate(req, entries, 24)
        resp.text = render(
            page=page, view='people', number=number, q=q, user=req.user,
            placeholder="Find people", entries=entries, errors={}, limit=24
        )


class DiscoverResource:
    def build_query(self, terms):
        query = Q()
        for term in terms:
            query &= Q(content__icontains=term)
        return query

    def fetch_entries(self, terms):
        if terms:
            f = self.build_query(terms)
        else:
            last_ids = User.objects.annotate(last=Max('comments')).values('last')
            f = Q(id__in=last_ids)
        return Comments.filter(f).order_by('-id').prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, page, number = paginate(req, self.fetch_entries(terms))
        resp.text = render(
            page=page, view='discover', number=number, q=q, errors={},
            placeholder="Search content", user=req.user, entries=entries
        )


class TrendingResource:
    def fetch_entries(self):
        sampling = Comment.objects.filter(parent=None).exclude(
            kids=None
        ).order_by('-id').values('id')[:24]
        entries = Comments.filter(id__in=sampling).order_by('-replies', '-id')
        return entries.prefetch_related(PFR)

    @before(auth_user)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries())
        resp.text = render(
            page=page, view='trending', number=number, user=req.user, entries=entries
        )


class LinksResource:
    def fetch_entries(self, req):
        entries = Comments.exclude(link='').order_by('-id')
        return entries.prefetch_related(PFR)

    @before(auth_user)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req))
        resp.text = render(
            page=page, view='links', number=number, user=req.user, entries=entries
        )


class GroupsResource:
    def fetch_entries(self):
        threads = Room.objects.annotate(thread=Max(
            'threads', filter=Q(threads__parent=None))
        ).values('thread')
        entries = Comments.filter(id__in=threads).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp):
        q = req.params.get('q', '').strip()
        hashtag = q[1:] if q.startswith('#') else q
        errors = {}
        if hashtag:
            errors['hashtag'] = valid_hashtag(hashtag)
            errors = {k: v for k, v in errors.items() if v}
            if not errors:
                room, _ = Room.objects.get_or_create(name=q.lower())
                raise HTTPFound(f"/group/{room}")
        entries, page, number = paginate(req, self.fetch_entries())
        resp.text = render(
            page=page, view='groups', number=number, user=req.user, q=q,
            entries=entries, errors=errors, placeholder="Create or find a #group"
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


class DetailsResource:
    social = ['dribbble', 'github', 'instagram', 'linkedin', 'spotify', 'youtube']
    phone = ['code', 'number']
    wallet = ['coin', 'id']

    def update(self, form, d, fields, is_lower=False):
        for field in fields:
            value = form.getvalue(field, '').strip()
            if value:
                d[field] = value.lower() if is_lower else value

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.text = render(
            page='details', view='details', user=req.user, form=form, errors={}
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f, s, p, w = {}, {}, {}, {}
        self.update(form, s, self.social, True)
        self.update(form, p, self.phone)
        self.update(form, w, self.wallet)
        errors = {}
        for field, value in s.items():
            errors[field] = valid_handle(value)
        errors['phone'] = valid_phone(p.get('code', ''), p.get('number', ''))
        errors['wallet'] = valid_wallet(w.get('coin', ''), w.get('id', ''))
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            f.update(p)
            f.update(s)
            f.update(w)
            resp.text = render(
                page='details', view='details', fields=f,
                user=req.user, errors=errors, form=form
            )
        else:
            req.user.phone = p
            req.user.social = s
            req.user.wallet = w
            req.user.save(update_fields=['phone', 'social', 'wallet'])
            raise HTTPFound(f"/{req.user}")


class ProfileResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        resp.text = render(
            page='profile', view='profile',
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
        f['location'] = get_location(form)
        f['description'] = get_content(form, 'description')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = profiling(f, req.user.id)
        if errors:
            resp.text = render(
                page='profile', view='profile',
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
                    'created_at': utc_timestamp(),
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
            raise HTTPFound('/unlock')
