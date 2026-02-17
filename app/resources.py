from django.db.models import Count, Prefetch, Q, Max
from emoji import demojize
from falcon import HTTPFound, HTTPNotFound, before
from strictyaml import as_document

from app.forms import get_content, get_emoji, get_location, get_metadata, get_name
from app.hooks import auth_user, login_required
from app.jinja import render
from app.models import Bond, Chat, Post, Save, User
from app.utils import build_hash, utc_timestamp, verify_hash
from app.validation import (authentication, profiling, registration,
                            valid_content, valid_handle, valid_password, valid_phone,
                            valid_reply, valid_thread)
from project.settings import FERNET, MAX_AGE

Posts = Post.objects.annotate(
    replies=Count('descendants')
).select_related('created_by')

PPFR = Prefetch('parent', Posts)
PFR = Prefetch('kids', Posts.order_by('-id'))
RPFR = Prefetch('kids', Posts.prefetch_related(PFR))


def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    number = int(p) if p.isdecimal() and int(p) else 0
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

    @before(auth_user)
    def on_get_api(self, req, resp):
        resp.text = render(
            page='api', view='about', user=req.user
        )

    @before(auth_user)
    def on_get_directory(self, req, resp):
        users = User.objects.exclude(posts=None).order_by('-id').values_list('emoji', 'username')
        odds = [u for i, u in enumerate(users) if i % 2 == 0]
        evens = [u for i, u in enumerate(users) if i % 2 == 1]
        resp.text = render(
            page='directory', view='about', user=req.user, users=zip(evens, odds)
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
        threads = Post.objects.filter(parent=None).annotate(Count('kids')).exclude(kids__count=0)
        replies = Post.objects.exclude(parent=None)
        posts = threads.union(replies).values_list('id')
        subs = Post.objects.values_list('hashtag').distinct()
        users = User.objects.exclude(posts=None).values_list('username')
        posts_urls = [f"https://subreply.com/reply/{p}" for p, in posts]
        sub_urls = [f"https://subreply.com/sub/{s}" for s, in subs]
        user_urls = [f"https://subreply.com/{u}" for u, in users]
        urls = sorted(posts_urls + sub_urls + user_urls)
        resp.text = "\n".join(urls)


class IntroResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        resp.text = render(
            page='intro', view='intro', user=req.user
        )


class FeedResource:
    placeholder = "What are you up to?"

    def fetch_entries(self, user):
        friends = Bond.objects.filter(created_by=user).values('to_user_id')
        entries = Posts.filter(created_by__in=friends).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

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
            extra['link'] = links[0] if links else ''
            extra['hashtag'] = hashtags[0] if hashtags else ''
            extra['at_user'] = User.objects.get(
                username=mentions[0]
            ) if mentions else None
            th, is_new = Post.objects.get_or_create(
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            raise HTTPFound('/')


class ReplyResource:
    def fetch_entries(self, parent):
        replies = list(
            Posts.filter(ancestors=parent).order_by('-id').select_related('parent')
        )
        by_parent = {}
        for reply in replies:
            by_parent.setdefault(reply.parent_id, []).append(reply)
        for reply in replies:
            reply.tree_kids = by_parent.get(reply.id, [])
        return by_parent.get(parent.id, [])

    def fetch_ancestors(self, parent):
        return Posts.filter(
            id__in=parent.ancestors.values('id')
        ).order_by('id').prefetch_related(PPFR)

    @before(auth_user)
    def on_get(self, req, resp, id):
        parent = Posts.filter(id=id).first()
        if not parent:
            raise HTTPNotFound
        duplicate = Post.objects.filter(
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
        parent = Posts.filter(id=id).select_related('parent').first()
        form = req.get_media()
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
                page='reply', view='reply', content=content,
                user=req.user, entry=parent, errors=errors,
                entries=entries, ancestors=ancestors, duplicate=False
            )
        else:
            extra = {}
            extra['link'] = links[0] if links else ''
            extra['hashtag'] = hashtags[0] if hashtags else ''
            extra['at_user'] = User.objects.get(
                username=mentions[0]
            ) if mentions else None
            re, is_new = Post.objects.get_or_create(
                parent=parent,
                to_user=parent.created_by,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            re.set_ancestors()
            raise HTTPFound(f"/reply/{re.id}")


class EditResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, id):
        entry = Posts.filter(id=id).prefetch_related(PPFR).first()
        if not entry or entry.created_by != req.user or entry.replies:
            raise HTTPNotFound
        ancestors = [entry.parent] if entry.parent_id else []
        resp.text = render(
            page='edit', view='edit', content=entry.content,
            user=req.user, entry=entry, errors={}, ancestors=ancestors
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, id):
        entry = Posts.filter(id=id).prefetch_related(PPFR).first()
        form = req.get_media()
        title = get_content(form, field='title')
        body = get_content(form, field='body', strip=False)
        content = get_content(form)
        hashtags, links, mentions = get_metadata(content)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            if entry.parent_id:
                errors['content'] = valid_reply(entry.parent, req.user, content, mentions)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            ancestors = [entry.parent] if entry.parent_id else []
            resp.text = render(
                page='edit', view='edit', content=content,
                user=req.user, entry=entry, errors=errors, ancestors=ancestors
            )
        else:
            previous_at_user = entry.at_user
            entry.title = title
            entry.body = body
            entry.content = content
            entry.edited_at = utc_timestamp()
            entry.link = links[0] if links else ''
            entry.hashtag = hashtags[0] if hashtags else ''
            entry.at_user = User.objects.get(
                username=mentions[0]
            ) if mentions else None
            if previous_at_user != entry.at_user:
                entry.mention_seen_at = .0
            entry.save()
            raise HTTPFound(f"/reply/{entry.id}")


class MemberResource:
    def fetch_entries(self, member):
        entries = Posts.filter(created_by=member).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        if req.user:
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
        saved_ids = Save.objects.filter(created_by=user).values('post__id')
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
        terms = [t.strip() for t in q.split() if t.strip()]
        entries = self.fetch_entries(terms)
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
            last_ids = User.objects.annotate(last_id=Max('posts')).values('last_id')
            f = Q(id__in=last_ids)
        return Posts.filter(f).order_by('-id').prefetch_related(PFR, PPFR)

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, page, number = paginate(req, self.fetch_entries(terms))
        resp.text = render(
            page=page, view='discover', number=number, q=q,
            user=req.user, entries=entries, errors={},
            placeholder=self.placeholder
        )


class TrendingResource:
    limit = 5 * 16 + 8

    def fetch_entries(self):
        sample = Post.objects.filter(parent=None).filter(kids__isnull=False).order_by('-id').values('id')[:self.limit]
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
    def fetch_entries(self, req, member):
        entries = Chat.objects.filter(
            Q(created_by=req.user.id, to_user=member.id) | Q(created_by=member.id, to_user=req.user.id)
        ).order_by('-id')
        return entries.select_related('created_by', 'to_user')

    def clear_messages(self, req, member):
        Chat.objects.filter(
            created_by=member, to_user=req.user, seen_at=.0
        ).update(seen_at=utc_timestamp())

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        entries, page, number = paginate(req, self.fetch_entries(req, member))
        forward = Chat.objects.filter(created_by=req.user, to_user=member).exists()
        backward = Chat.objects.filter(created_by=member, to_user=req.user).exists()
        blocked = True if forward and not backward else False
        resp.text = render(
            page=page, view='message', number=number, user=req.user, errors={},
            entries=entries, member=member, blocked=blocked
        )
        if req.user.received.filter(created_by=member, seen_at=.0).count():
            self.clear_messages(req, member)

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp, username):
        member = User.objects.filter(username=username.lower()).first()
        form = req.get_media()
        content = get_content(form)
        if not content:
            raise HTTPFound(f"/{username}/message")
        errors = {}
        errors['content'] = valid_content(content, req.user)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            entries, page, number = paginate(req, self.fetch_entries(req, member))
            resp.text = render(
                page=page, view='message', number=number, user=req.user,
                member=member, entries=entries, content=content, errors=errors
            )
        else:
            msg, is_new = Chat.objects.get_or_create(
                to_user=member,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                seen_at=utc_timestamp() if member == req.user else .0
            )
            raise HTTPFound(f"/{username}/message")


class WriteResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        resp.text = render(
            page='write', view='write', user=req.user, errors={}, form={}
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = req.get_media()
        title = get_content(form, field='title')
        body = get_content(form, field='body', strip=False)
        content = get_content(form)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content']:
            errors['content'] = valid_thread(content)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            resp.text = render(
                page='write', view='write', user=req.user, errors=errors, form=form
            )
        else:
            hashtags, links, mentions = get_metadata(content)
            extra = {}
            extra['link'] = links[0] if links else ''
            extra['hashtag'] = hashtags[0] if hashtags else ''
            extra['at_user'] = User.objects.get(
                username=mentions[0]
            ) if mentions else None
            article, is_new = Post.objects.get_or_create(
                title=title,
                content=content,
                body=body,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            raise HTTPFound(f"/reply/{article.id}")


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
                change_errors=errors, form=form
            )
        else:
            req.user.password = build_hash(password1)
            req.user.save()
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
                export_errors=errors, form=form
            )
        else:
            posts = Post.objects.filter(
                created_by=req.user
            ).order_by('-id').prefetch_related('parent__created_by')
            data = []
            for post in posts:
                d = {}
                if post.parent:
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
                delete_errors=errors, form=form
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
        f, s, p = {}, {}, {}
        self.update(form, s, self.social)
        self.update(form, p, self.phone)
        errors = {}
        for field, value in s.items():
            errors[field] = valid_handle(value)
        errors['phone'] = valid_phone(p.get('code', ''), p.get('number', ''))
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            f.update(p)
            f.update(s)
            resp.text = render(
                page='details', view='details', user=req.user,
                errors=errors, form=form
            )
        else:
            req.user.phone = p
            req.user.social = s
            req.user.save(update_fields=['phone', 'social'])
            raise HTTPFound(f"/{req.user}")


class ProfileResource:
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
        f = {}
        f['username'] = form.get('username', '').strip().lower()
        f['email'] = form.get('email', '').strip().lower()
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.get('birthday', '').strip()
        f['location'] = get_location(form)
        f['link'] = form.get('link', '').strip().lower()
        f['description'] = get_content(form, 'description')
        errors = profiling(f, req.user.id)
        if errors:
            resp.text = render(
                page='profile', view='profile', user=req.user,
                errors=errors, form=form
            )
        else:
            for field, value in f.items():
                if getattr(req.user, field, '') != value:
                    setattr(req.user, field, value)
            req.user.save()
            raise HTTPFound('/{0}'.format(req.user))


class LoginResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        resp.text = render(page='login', view='login', errors={}, form={})

    def on_post(self, req, resp):
        form = req.get_media()
        username = form.get('username', '').strip().lower()
        password = form.get('password', '')
        errors, user = authentication(username, password)
        if errors:
            resp.text = render(
                page='login', view='login', errors=errors, form=form
            )
        else:
            token = FERNET.encrypt(str(user.id).encode()).decode()
            resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
            raise HTTPFound('/feed')


class LogoutResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        resp.unset_cookie('identity')
        raise HTTPFound('/discover')


class RegisterResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        resp.text = render(
            page='register', view='register', errors={}, form={}
        )

    def on_post(self, req, resp):
        form = req.get_media()
        f = {}
        f['username'] = form.get('username', '').strip().lower()
        f['email'] = form.get('email', '').strip().lower()
        f['password1'] = form.get('password1', '')
        f['password2'] = form.get('password2', '')
        f['first_name'] = get_name(form, 'first')
        f['last_name'] = get_name(form, 'last')
        f['emoji'] = get_emoji(form)
        f['birthday'] = form.get('birthday', '').strip()
        f['location'] = form.get('location', '')
        errors = registration(f)
        if errors:
            resp.text = render(
                page='register', view='register', errors=errors, form=form
            )
        else:
            user, is_new = User.objects.get_or_create(
                username=f['username'],
                defaults={
                    'created_at': utc_timestamp(),
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
            # create self bond
            Bond.objects.get_or_create(
                created_at=utc_timestamp(), seen_at=utc_timestamp(),
                created_by=user, to_user=user
            )
            # set id cookie
            token = FERNET.encrypt(str(user.id).encode()).decode()
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
        email = FERNET.decrypt(token.encode()).decode()
        user = User.objects.filter(email=email).first()
        token = FERNET.encrypt(str(user.id).encode()).decode()
        resp.set_cookie('identity', token, path="/", max_age=MAX_AGE)
        raise HTTPFound('/feed')

    def on_post(self, req, resp):
        form = req.get_media()
        email = form.get('email', '').strip().lower()
        errors = {}
        user = User.objects.filter(email=email).first()
        if not user:
            errors['email'] = "Email doesn't exist"
        if errors:
            resp.text = render(
                page='recover', view='recover', errors=errors, form=form
            )
        else:
            # generate token
            token = FERNET.encrypt(user.email.encode()).decode()
            # compose message
            admin = User.objects.get(id=1)
            if Chat.objects.filter(
                content__startswith="Send https://subreply.com/recover",
                content__endswith=f"to {user.email}.",
                created_by=user,
                to_user=admin,
            ).exists():
                errors['email'] = "Message couldn't be sent"
            else:
                m, is_new = Chat.objects.get_or_create(
                    content=f"Send https://subreply.com/recover/{token} to {user.email}.",
                    created_by=user,
                    to_user=admin,
                    defaults={
                        'created_at': utc_timestamp(),
                    }
                )
                # callback
                if is_new:
                    errors['email'] = "Please wait for your recovery link"
                else:
                    errors['email'] = "Message couldn't be sent"
            resp.text = render(
                page='recover', view='recover', errors=errors, form=form
            )
