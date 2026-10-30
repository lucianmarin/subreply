from django.db.models import Max, Prefetch, Q, Subquery
from emoji import demojize
from falcon import HTTPFound, HTTPNotFound, before
from strictyaml import as_document

from app.forms import get_content, get_emoji, get_location, get_metadata, get_name
from app.hooks import auth_user, login_required
from app.jinja import render
from app.models import Bond, Chat, Post, Save, User
from app.utils import build_hash, utc_timestamp, verify_hash
from app.validation import (
    authentication, valid_birthday, valid_content, valid_description,
    valid_email, valid_emoji, valid_first_name, valid_full_name, valid_handle,
    valid_last_name, valid_link, valid_location, valid_password, valid_phone,
    valid_reply, valid_thread, valid_username
)
from project.settings import FERNET, MAX_AGE

Posts = Post.objects.select_related('created_by')

PPFR = Prefetch('parent', Posts)
PFR = Prefetch('kids', Posts.order_by('-id'))
RPFR = Prefetch('kids', Posts.order_by('-id').prefetch_related(PFR))
USQ = lambda m: Subquery(User.objects.filter(username=m[0]).values('id')[:1]) if m else None


def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    if p.isdecimal() and int(p) > 1:
        number = int(p)
    else:
        number = 1
    page = 'loader' if number > 1 else 'regular'
    index = (number - 1) * limit
    return qs[index:index + limit], page, number


class MainResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        raise HTTPFound('/discover')


class AboutResource:
    @before(auth_user)
    def on_get(self, req, resp):
        users = User.objects.in_bulk([1, 2])
        emo = User.objects.exclude(
            id__in=[1, 2]
        ).exclude(emoji="").order_by("?").first()
        resp.text = render(
            page='about', view='about', user=req.user,
            luc=users[1], sub=users[2], emo=emo
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

    @before(auth_user)
    def on_get_api(self, req, resp):
        resp.text = render(
            page='api', view='about', user=req.user
        )

    @before(auth_user)
    def on_get_directory(self, req, resp):
        users = User.objects.exclude(posts=None).order_by('username').values_list('emoji', 'username')
        groups = {}
        for emoji, username in users:
            c = username[0]
            if c.isdigit():
                key = '0-9 numbers'
            elif c == '_':
                key = '_ character'
            else:
                key = f'{c.upper()} letter'
            groups.setdefault(key, []).append((emoji, username))
        groups = {
            f"{k} &mdash; {len(v)} users": list(zip(v[::2], v[1::2] + [('', '')]))
            for k, v in sorted(groups.items(), key=lambda x: (x[0] != '_ character', x[0]))
        }
        resp.text = render(
            page='directory', view='about', user=req.user, groups=groups
        )


class TxtResource:
    def on_get_bots(self, req, resp):
        lines = (
            "User-agent: *",
            "",
            "Sitemap: https://subreply.com/sitemap.txt"
        )
        resp.text = "\n".join(lines)

    def on_get_map(self, req, resp):
        posts = Post.objects.exclude(parent=None, replies=0).values_list('id', flat=True)
        users = User.objects.exclude(posts=None).values_list('username', flat=True)
        posts_urls = [f"https://subreply.com/reply/{p}" for p in posts]
        user_urls = [f"https://subreply.com/{u}" for u in users]
        urls = sorted(posts_urls + user_urls)
        resp.text = "\n".join(urls)


class FeedResource:
    placeholder = "Say something"

    def fetch_entries(self, user):
        friends = Bond.objects.filter(created_by=user).values('to_user_id')
        entries = Posts.filter(created_by__in=friends).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    def validate_entry(self, content, user):
        errors = {}
        errors['content'] = valid_content(content, user)
        if not errors['content']:
            errors['content'] = valid_thread(content)
        return {k: v for k, v in errors.items() if v}

    def create_entry(self, content, user):
        hashtags, links, mentions = get_metadata(content)
        return Post.objects.create(
            content=content,
            created_by=user,
            created_at=utc_timestamp(),
            link=links[0] if links else '',
            hashtag=hashtags[0] if hashtags else '',
            at_user_id=USQ(mentions),
        )

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='feed', number=number, content='',
            user=req.user, entries=entries, errors={},
            placeholder=self.placeholder
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = req.get_media()
        content = get_content(form)
        if not content:
            raise HTTPFound('/')
        errors = self.validate_entry(content, req.user)
        if errors:
            entries = self.fetch_entries(req.user)[:16]
            resp.text = render(
                page='regular', view='feed', content=content, number=1,
                user=req.user, entries=entries, errors=errors,
                placeholder=self.placeholder
            )
        else:
            self.create_entry(content, req.user)
            raise HTTPFound('/')


class ReplyResource:
    def fetch_entries(self, parent):
        return Posts.filter(parent=parent).order_by('-id').prefetch_related(RPFR)

    def fetch_ancestors(self, parent):
        return Posts.filter(
            id__in=parent.ancestors.values('id')
        ).order_by('id')

    def has_duplicate(self, parent, user):
        return Post.objects.filter(
            parent=parent, created_by=user
        ).exists() if user else True

    def validate_entry(self, parent, content, user):
        errors = {}
        errors['content'] = valid_content(content, user)
        if not errors['content']:
            _, _, mentions = get_metadata(content)
            errors['content'] = valid_reply(parent, user, content, mentions)
        return {k: v for k, v in errors.items() if v}

    def create_entry(self, parent, content, user):
        hashtags, links, mentions = get_metadata(content)
        re = Post.objects.create(
            parent=parent,
            created_by=user,
            to_user=parent.created_by,
            content=content,
            created_at=utc_timestamp(),
            link=links[0] if links else '',
            hashtag=hashtags[0] if hashtags else '',
            at_user_id=USQ(mentions),
        )
        re.set_ancestors()
        re.add_replies()
        parent.replies += 1
        return re

    @before(auth_user)
    def on_get(self, req, resp, id):
        parent = Posts.filter(id=id).first()
        if not parent:
            raise HTTPNotFound
        duplicate = self.has_duplicate(parent, req.user)
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
        parent = Posts.filter(id=id).first()
        if not parent:
            raise HTTPNotFound
        form = req.get_media()
        content = get_content(form)
        if not content:
            raise HTTPFound(f"/reply/{id}")
        if existing := Post.objects.filter(parent=parent, created_by=req.user).first():
            raise HTTPFound(f"/reply/{existing.id}")
        errors = self.validate_entry(parent, content, req.user)
        if errors:
            ancestors = self.fetch_ancestors(parent)
            entries = self.fetch_entries(parent)
            resp.text = render(
                page='reply', view='reply', content=content,
                user=req.user, entry=parent, errors=errors,
                entries=entries, ancestors=ancestors, duplicate=False
            )
        else:
            re = self.create_entry(parent, content, req.user)
            raise HTTPFound(f"/reply/{re.id}")


class EditResource:
    def fetch_entry(self, id):
        return Posts.filter(id=id).prefetch_related(PPFR).first()

    def validate_entry(self, entry, content, user):
        errors = {}
        errors['content'] = valid_content(content, user)
        if not errors['content'] and content.lower() != entry.content.lower():
            if entry.parent_id:
                _, _, mentions = get_metadata(content)
                errors['content'] = valid_reply(entry.parent, user, content, mentions)
            else:
                errors['content'] = valid_thread(content)
        return {k: v for k, v in errors.items() if v}

    def update_entry(self, entry, content):
        _, _, prev_mentions = get_metadata(entry.content)
        hashtags, links, mentions = get_metadata(content)
        entry.content = content
        entry.edited_at = utc_timestamp()
        entry.link = links[0] if links else ''
        entry.hashtag = hashtags[0] if hashtags else ''
        if mentions != prev_mentions:
            entry.at_user_id = USQ(mentions)
            entry.mention_seen_at = .0
        entry.save()
        return entry

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, id):
        entry = self.fetch_entry(id)
        if not entry or entry.created_by_id != req.user.id or entry.replies:
            raise HTTPNotFound
        ancestors = [entry.parent] if entry.parent_id else []
        resp.text = render(
            page='edit', view='edit', content=entry.content,
            user=req.user, entry=entry, errors={}, ancestors=ancestors
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, id):
        entry = self.fetch_entry(id)
        if not entry or entry.created_by_id != req.user.id or entry.replies:
            raise HTTPNotFound
        form = req.get_media()
        content = get_content(form)
        if content == entry.content:
            raise HTTPFound(f"/reply/{entry.id}")
        errors = self.validate_entry(entry, content, req.user)
        if errors:
            ancestors = [entry.parent] if entry.parent_id else []
            resp.text = render(
                page='edit', view='edit', content=content,
                user=req.user, entry=entry, errors=errors, ancestors=ancestors
            )
        else:
            self.update_entry(entry, content)
            raise HTTPFound(f"/reply/{entry.id}")


class MemberResource:
    def fetch_member(self, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        return member

    def fetch_entries(self, member):
        entries = Posts.filter(created_by=member).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp, username):
        member = self.fetch_member(username)
        if req.user and req.user.id != member.id:
            is_followed = Bond.objects.filter(created_by=member, to_user=req.user).exists()
        else:
            is_followed = None
        entries, page, number = paginate(req, self.fetch_entries(member))
        resp.text = render(
            page=page, view='member', number=number, errors={},
            user=req.user, member=member, entries=entries, is_followed=is_followed
        )


class FollowingResource:
    def fetch_entries(self, user):
        entries = Bond.objects.filter(created_by=user).exclude(to_user=user)
        return entries.order_by('-id').select_related('to_user')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user), 24)
        resp.text = render(
            page=page, view='following', number=number,
            user=req.user, entries=entries, limit=24
        )


class FollowersResource:
    def fetch_entries(self, user):
        entries = Bond.objects.filter(to_user=user).exclude(created_by=user)
        return entries.order_by('-id').select_related('created_by')

    def clear_followers(self, user):
        Bond.objects.filter(
            to_user=user, seen_at=.0
        ).update(seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user), 24)
        resp.text = render(
            page=page, view='followers', number=number,
            user=req.user, entries=entries, limit=24
        )
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsResource:
    def fetch_entries(self, user):
        entries = Posts.filter(at_user=user).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    def clear_mentions(self, user):
        Post.objects.filter(
            at_user=user, mention_seen_at=.0
        ).update(mention_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='mentions', number=number,
            user=req.user, entries=entries
        )
        if req.user.notif_mentions:
            self.clear_mentions(req.user)


class RepliesResource:
    def fetch_entries(self, user):
        entries = Posts.filter(to_user=user).order_by('-id')
        return entries.prefetch_related(PPFR)

    def clear_replies(self, user):
        Post.objects.filter(
            to_user=user, reply_seen_at=.0
        ).update(reply_seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='replies', number=number,
            user=req.user, entries=entries
        )
        if req.user.notif_replies:
            self.clear_replies(req.user)


class SavedResource:
    def fetch_entries(self, user):
        saved_ids = Save.objects.filter(created_by=user).values('post_id')
        entries = Posts.filter(id__in=saved_ids).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req.user))
        resp.text = render(
            page=page, view='saved', number=number,
            user=req.user, entries=entries
        )


class DestroyResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, username):
        if not req.user.id == 1:
            raise HTTPFound('/people')
        username = username.lower()
        User.objects.filter(username=username).delete()
        raise HTTPFound('/people')


class PeopleResource:
    fields = [
        "username", "first_name", "last_name", "email",
        "description", "birthday", "location", "emoji", "link"
    ]
    placeholder = "Find people"

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
        qs = User.objects.filter(q)
        return qs.order_by('-seen_at')

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        entries = self.fetch_entries(q.split())
        entries, page, number = paginate(req, entries, 24)
        resp.text = render(
            page=page, view='people', number=number, q=q,
            user=req.user, entries=entries, errors={}, limit=24,
            placeholder=self.placeholder
        )


class DiscoverResource:
    placeholder = "Search content"

    def build_query(self, terms):
        query = Q()
        for term in terms:
            query &= Q(content__icontains=term)
        return query

    def fetch_entries(self, terms):
        if terms:
            f = self.build_query(terms)
        else:
            last_ids = Post.objects.values('created_by_id').annotate(last_id=Max('id')).values('last_id')
            f = Q(id__in=last_ids)
        return Posts.filter(f).order_by('-id').prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        entries, page, number = paginate(req, self.fetch_entries(q.split()))
        resp.text = render(
            page=page, view='discover', number=number, q=q,
            user=req.user, entries=entries, errors={},
            placeholder=self.placeholder
        )


class TrendingResource:
    limit = 24

    def fetch_entries(self):
        sample = Post.objects.filter(parent=None).exclude(replies=0).order_by('-id').values('id')[:self.limit]
        entries = Posts.filter(id__in=sample).order_by('-replies', '-id')
        return entries.prefetch_related(PFR)

    @before(auth_user)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries())
        resp.text = render(
            page=page, view='trending', number=number,
            user=req.user, entries=entries
        )


class MessagesResource:
    def fetch_entries(self, req):
        last_ids = Chat.objects.filter(
            to_user=req.user
        ).values('created_by_id').annotate(last_id=Max('id')).values('last_id')
        entries = Chat.objects.filter(id__in=last_ids).order_by('-id')
        return entries.select_related('created_by')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries, page, number = paginate(req, self.fetch_entries(req))
        resp.text = render(
            page=page, view='messages', number=number,
            user=req.user, entries=entries
        )


class MessageResource:
    def fetch_member(self, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        return member

    def fetch_entries(self, req, member):
        entries = Chat.objects.filter(
            Q(created_by=req.user.id, to_user=member.id) | Q(created_by=member.id, to_user=req.user.id)
        ).order_by('-id')
        return entries.select_related('created_by', 'to_user')

    def clear_messages(self, req, member):
        Chat.objects.filter(
            created_by=member, to_user=req.user, seen_at=.0
        ).update(seen_at=utc_timestamp())

    def is_blocked(self, user, member):
        return (
            Chat.objects.filter(created_by=user, to_user=member).exists() and
            not Chat.objects.filter(created_by=member, to_user=user).exists()
        )

    def validate_message(self, content, user, member):
        errors = {}
        errors['content'] = valid_content(content, user)
        if not errors['content'] and self.is_blocked(user, member):
            errors['request'] = "Wait for the recipient to respond"
        return {k: v for k, v in errors.items() if v}

    def create_entry(self, user, member, content):
        return Chat.objects.create(
            to_user=member,
            content=content,
            created_at=utc_timestamp(),
            created_by=user,
            seen_at=utc_timestamp() if member.id == user.id else .0
        )

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, username):
        member = self.fetch_member(username)
        entries, page, number = paginate(req, self.fetch_entries(req, member))
        blocked = self.is_blocked(req.user, member)
        resp.text = render(
            page=page, view='message', number=number, content='',
            user=req.user, errors={}, entries=entries, member=member, blocked=blocked
        )
        self.clear_messages(req, member)

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, username):
        member = self.fetch_member(username)
        form = req.get_media()
        content = get_content(form)
        if not content:
            raise HTTPFound(f"/{member.username}/message")
        errors = self.validate_message(content, req.user, member)
        if errors:
            entries, page, number = paginate(req, self.fetch_entries(req, member))
            resp.text = render(
                page=page, view='message', number=number, user=req.user,
                member=member, entries=entries, content=content, errors=errors,
                blocked='request' in errors
            )
        else:
            self.create_entry(req.user, member, content)
            raise HTTPFound(f"/{member.username}/message")


class AccountResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        resp.text = render(
            page='account', view='account', user=req.user,
            change_errors={}, export_errors={}, delete_errors={}, form={}
        )

    @before(auth_user)
    @before(login_required)
    def on_post_change(self, req, resp):
        form = req.get_media()
        password1 = form.get('password1', '')
        password2 = form.get('password2', '')
        errors = {}
        errors['password'] = valid_password(password1, password2)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            resp.text = render(
                page='account', view='account', user=req.user,
                change_errors=errors, export_errors={}, delete_errors={}, form=form
            )
        else:
            req.user.password = build_hash(password1)
            req.user.save(update_fields=['password'])
            resp.unset_cookie('identity')
            raise HTTPFound('/login')

    @before(auth_user)
    @before(login_required)
    def on_post_export(self, req, resp):
        form = req.get_media()
        username = form.get('username', '').strip().lower()
        errors = {}
        if req.user.username != username:
            errors['username'] = "Username doesn't match"
        if errors:
            resp.text = render(
                page='account', view='account', user=req.user,
                change_errors={}, export_errors=errors, delete_errors={}, form=form
            )
        else:
            posts = Post.objects.filter(
                created_by=req.user
            ).order_by('-id').select_related('parent__created_by')
            data = []
            for post in posts:
                d = {}
                if post.parent_id:
                    p = {}
                    p['username'] = post.parent.created_by.username
                    p['content'] = post.parent.content
                    d['parent'] = p
                d['content'] = post.content
                d['created'] = post.created_at
                if post.edited_at:
                    d['edited'] = post.edited_at
                data.append(d)
            data = data if data else ""
            resp.content_type = "application/x-yaml"
            resp.downloadable_as = f"subreply-{username}.yaml"
            resp.text = as_document(data).as_yaml()

    @before(auth_user)
    @before(login_required)
    def on_post_delete(self, req, resp):
        form = req.get_media()
        confirm = form.get('confirm', '')
        errors = {}
        if not verify_hash(confirm, req.user.password):
            errors['confirm'] = "Password doesn't match"
        if errors:
            resp.text = render(
                page='account', view='account', user=req.user,
                change_errors={}, export_errors={}, delete_errors=errors, form=form
            )
        else:
            req.user.delete()
            resp.unset_cookie('identity')
            raise HTTPFound('/discover')


class DetailsResource:
    social = ['github', 'instagram', 'linkedin', 'reddit', 'paypal', 'spotify', 'x']
    phone = ['code', 'number']

    def update(self, form, d, fields):
        for field in fields:
            value = form.get(field, '').strip()
            if value:
                d[field] = value.lower()

    def parse_form(self, form):
        s, p = {}, {}
        self.update(form, s, self.social)
        self.update(form, p, self.phone)
        return s, p

    def validate_details(self, s, p, user):
        errors = {}
        for field, value in s.items():
            if value != user.social.get(field):
                errors[field] = valid_handle(value)
        if p != user.phone:
            errors['phone'] = valid_phone(p.get('code', ''), p.get('number', ''))
        return {k: v for k, v in errors.items() if v}

    def update_user(self, user, s, p):
        fields = []
        if p != user.phone:
            user.phone = p
            fields.append('phone')
        if s != user.social:
            user.social = s
            fields.append('social')
        if fields:
            user.save(update_fields=fields)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        resp.text = render(
            page='details', view='details', user=req.user,
            errors={}, form={}
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = req.get_media()
        s, p = self.parse_form(form)
        errors = self.validate_details(s, p, req.user)
        if errors:
            resp.text = render(
                page='details', view='details', user=req.user,
                errors=errors, form=form
            )
        else:
            self.update_user(req.user, s, p)
            raise HTTPFound(f"/{req.user}")


class ProfileResource:
    def parse_form(self, form):
        return {
            'username': form.get('username', '').strip().lower(),
            'email': form.get('email', '').strip().lower(),
            'first_name': get_name(form, 'first'),
            'last_name': get_name(form, 'last'),
            'emoji': get_emoji(form),
            'birthday': form.get('birthday', '').strip(),
            'location': get_location(form),
            'link': form.get('link', '').strip().lower(),
            'description': get_content(form, 'description'),
        }

    def validate_profile(self, f, user):
        errors = {}
        if f['username'] != user.username:
            errors['username'] = valid_username(f['username'], user_id=user.id)
        if f['email'] != user.email:
            errors['email'] = valid_email(f['email'], user_id=user.id)
        if f['first_name'] != user.first_name:
            errors['first_name'] = valid_first_name(f['first_name'])
        if f['last_name'] != user.last_name:
            errors['last_name'] = valid_last_name(f['last_name'])
        if f['emoji'] != user.emoji:
            errors['emoji'] = valid_emoji(f['emoji'])
        if not (errors.get('emoji') or errors.get('first_name') or errors.get('last_name')):
            if (f['emoji'], f['first_name'], f['last_name']) != (user.emoji, user.first_name, user.last_name):
                errors['full_name'] = valid_full_name(
                    f['emoji'], f['first_name'], f['last_name'], user_id=user.id
                )
        if f['birthday'] != user.birthday:
            errors['birthday'] = valid_birthday(f['birthday'])
        if f['location'] != user.location:
            errors['location'] = valid_location(f['location'])
        if f['link'] != user.link:
            errors['link'] = valid_link(f['link'], user_id=user.id)
        if f['description'] != user.description:
            errors['description'] = valid_description(f['description'], user)
        return {k: v for k, v in errors.items() if v}

    def update_user(self, user, f):
        fields = []
        for field, value in f.items():
            if getattr(user, field, '') != value:
                setattr(user, field, value)
                fields.append(field)
        if fields:
            user.save(update_fields=fields)

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        resp.text = render(
            page='profile', view='profile', user=req.user, errors={}, form={}
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = req.get_media()
        f = self.parse_form(form)
        errors = self.validate_profile(f, req.user)
        if errors:
            resp.text = render(
                page='profile', view='profile', user=req.user,
                errors=errors, form=form
            )
        else:
            self.update_user(req.user, f)
            raise HTTPFound('/{0}'.format(req.user))


class LoginResource:
    def authenticate_user(self, form):
        username = form.get('username', '').strip().lower()
        password = form.get('password', '')
        return authentication(username, password)

    def build_token(self, user):
        return FERNET.encrypt(str(user.id).encode()).decode()

    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        resp.text = render(page='login', view='login', errors={}, form={})

    def on_post(self, req, resp):
        form = req.get_media()
        errors, user = self.authenticate_user(form)
        if errors:
            resp.text = render(
                page='login', view='login', errors=errors, form=form
            )
        else:
            token = self.build_token(user)
            resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class LogoutResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        resp.unset_cookie('identity')
        raise HTTPFound('/discover')


class RegisterResource:
    def parse_form(self, form):
        return {
            'username': form.get('username', '').strip().lower(),
            'email': form.get('email', '').strip().lower(),
            'password1': form.get('password1', ''),
            'password2': form.get('password2', ''),
            'first_name': get_name(form, 'first'),
            'last_name': get_name(form, 'last'),
            'emoji': get_emoji(form),
            'birthday': form.get('birthday', '').strip(),
            'location': get_location(form),
        }

    def validate_registration(self, f):
        errors = {}
        errors['username'] = valid_username(f['username'])
        errors['email'] = valid_email(f['email'])
        errors['password'] = valid_password(f['password1'], f['password2'])
        errors['first_name'] = valid_first_name(f['first_name'])
        errors['last_name'] = valid_last_name(f['last_name'])
        errors['emoji'] = valid_emoji(f['emoji'])
        if not (errors['emoji'] or errors['first_name'] or errors['last_name']):
            errors['full_name'] = valid_full_name(
                f['emoji'], f['first_name'], f['last_name']
            )
        errors['birthday'] = valid_birthday(f['birthday'])
        errors['location'] = valid_location(f['location'])
        return {k: v for k, v in errors.items() if v}

    def create_user(self, f):
        user = User.objects.create(
            username=f['username'],
            created_at=utc_timestamp(),
            seen_at=utc_timestamp(),
            password=build_hash(f['password1']),
            email=f['email'],
            first_name=f['first_name'],
            last_name=f['last_name'],
            emoji=f['emoji'],
            birthday=f['birthday'],
            location=f['location'],
        )
        Bond.objects.create(
            created_by=user,
            to_user=user,
            created_at=utc_timestamp(),
            seen_at=utc_timestamp()
        )
        return user

    def build_token(self, user):
        return FERNET.encrypt(str(user.id).encode()).decode()

    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        resp.text = render(
            page='register', view='register', errors={}, form={}
        )

    def on_post(self, req, resp):
        form = req.get_media()
        f = self.parse_form(form)
        errors = self.validate_registration(f)
        if errors:
            resp.text = render(
                page='register', view='register', errors=errors, form=form
            )
        else:
            user = self.create_user(f)
            token = self.build_token(user)
            resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
            raise HTTPFound('/')


class RecoverResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        resp.text = render(
            page='recover', view='recover', errors={}, form={}
        )

    def on_get_link(self, req, resp, token):
        try:
            email = FERNET.decrypt(token.encode()).decode()
        except Exception:
            raise HTTPFound('/login')
        user = User.objects.filter(email=email).first()
        if not user:
            raise HTTPFound('/login')
        token = FERNET.encrypt(str(user.id).encode()).decode()
        resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
        raise HTTPFound('/feed')

    def on_post(self, req, resp):
        form = req.get_media()
        email = form.get('email', '').strip().lower()
        errors = {}
        user = User.objects.filter(email=email).first() if email else None
        if not user:
            errors['email'] = "Email doesn't exist"
        elif Chat.objects.filter(
            content__startswith="Send https://subreply.com/recover",
            content__endswith=f"to {user.email}.",
            created_by=user,
            to_user_id=1,
        ).exists():
            errors['email'] = "Request already sent"
        else:
            # generate token
            token = FERNET.encrypt(user.email.encode()).decode()
            # compose message
            Chat.objects.create(
                content=f"Send https://subreply.com/recover/{token} to {user.email}.",
                created_by=user,
                to_user_id=1,
                created_at=utc_timestamp(),
            )
            errors['email'] = "Please wait for your recovery link"
        resp.text = render(
            page='recover', view='recover', errors=errors, form=form
        )
