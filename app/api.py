from emoji import demojize
from falcon import HTTPNotFound
from falcon.hooks import before
from falcon.constants import MEDIA_JSON
from django.db.models import Count, F, Prefetch, Q, Max

from app.forms import get_content, get_emoji, get_location, get_metadata, get_name
from app.hooks import auth_required, auth_user
from app.models import Bond, Chat, Post, Save, User, Work
from app.serializers import build_entry, build_user, build_chat, build_work
from app.utils import build_hash, utc_timestamp, verify_hash
from app.validation import (authentication, registration, valid_content, valid_reply,
                            valid_thread)
from project.settings import FERNET

Posts = Post.objects.annotate(
    replies=Count('descendants')
).select_related('created_by')

PPFR = Prefetch('parent', Posts)
PFR = Prefetch('kids', Posts.order_by('-id'))
RPFR = Prefetch('kids', Posts.prefetch_related(PFR))

def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    number = int(p) if p.isdecimal() and int(p) else 0
    index = (number - 1) * limit
    return qs[index:index + limit], number


class LoginEndpoint:
    def on_post(self, req, resp):
        form = req.get_media()
        username = form.get('username', '')
        password = form.get('password', '')
        errors, user = authentication(username, password)
        resp.content_type = MEDIA_JSON
        if errors:
            resp.media = {'errors': errors}
        else:
            token = FERNET.encrypt(str(user.id).encode()).decode()
            resp.media = {
                "token": token,
                "user": build_user(user)
            }


class RegisterEndpoint:
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
        resp.content_type = MEDIA_JSON
        if errors:
            resp.media = {'errors': errors}
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
            # create self bond
            Bond.objects.get_or_create(
                created_at=utc_timestamp(), seen_at=utc_timestamp(),
                created_by=user, to_user=user
            )
            # generate token
            token = FERNET.encrypt(str(user.id).encode()).decode()
            resp.media = {
                "token": token,
                "user": build_user(user)
            }


class PostEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        parent = Posts.filter(id=form.get('parent', 0)).first()
        content = get_content(form)
        if not content:
            resp.media = {'error': 'content parameter is empty'}
            return
        hashtags, links, mentions = get_metadata(content)
        errors = {}
        errors['content'] = valid_content(content, req.user)
        if not errors['content'] and not parent:
            errors['content'] = valid_thread(content)
        if not errors['content'] and parent:
            errors['content'] = valid_reply(parent, req.user, content, mentions)
        errors = {k: v for k, v in errors.items() if v}
        if errors:
            resp.media = {'errors': errors}
        else:
            extra = {}
            extra['link'] = links[0] if links else ''
            extra['hashtag'] = hashtags[0] if hashtags else ''
            extra['at_user'] = User.objects.get(
                username=mentions[0]
            ) if mentions else None
            re, is_new = Post.objects.get_or_create(
                parent=parent,
                to_user=parent.created_by if parent else None,
                content=content,
                created_at=utc_timestamp(),
                created_by=req.user,
                **extra
            )
            re.set_ancestors()
            resp.media = build_entry(re, [], parents=True)


class FeedEndpoint:
    def fetch_entries(self, user):
        friends = Bond.objects.filter(created_by=user).values('to_user_id')
        entries = Posts.filter(created_by__in=friends).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        resp.content_type = MEDIA_JSON
        entries, page = paginate(req, self.fetch_entries(req.user))
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user.saves, parents=True) for entry in entries]
        }


class ReplyEndpoint:
    def fetch_entries(self, parent):
        return Posts.filter(parent=parent).order_by('-id').prefetch_related(RPFR)

    def fetch_ancestors(self, parent):
        return Posts.filter(
            id__in=parent.ancestors.values('id')
        ).order_by('id').prefetch_related(PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp, id):
        parent = Posts.filter(id=id).first()
        if not parent:
            raise HTTPNotFound
        ancestors = self.fetch_ancestors(parent)
        entries = self.fetch_entries(parent)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "entry": build_entry(parent, req.user.saves),
            "ancestors": [build_entry(entry, req.user.saves) for entry in ancestors],
            "entries": [build_entry(entry, req.user.saves, parents=True) for entry in entries]
        }


class MemberEndpoint:
    def fetch_entries(self, member):
        entries = Posts.filter(created_by=member).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp, username):
        username = username.lower()
        member = User.objects.filter(username=username).first()
        if not member:
            raise HTTPNotFound
        entries, page = paginate(req, self.fetch_entries(member))
        works = Work.objects.filter(created_by=member).order_by(
            F('end_date').desc(nulls_first=True), '-start_date'
        )
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "member": build_user(member),
            "entries": [build_entry(entry, req.user.saves, parents=True) for entry in entries],
            "works": [build_work(work) for work in works]
        }


class FollowingEndpoint:
    def fetch_entries(self, user):
        entries = Bond.objects.filter(created_by=user).exclude(to_user=user)
        return entries.order_by('-id').select_related('to_user')

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries(req.user), 24)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_user(entry.to_user) for entry in entries]
        }


class FollowersEndpoint:
    def fetch_entries(self, user):
        entries = Bond.objects.filter(to_user=user).exclude(created_by=user)
        return entries.order_by('-id').select_related('created_by')

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries(req.user), 24)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_user(entry.created_by) for entry in entries]
        }


class MentionsEndpoint:
    def fetch_entries(self, user):
        entries = Posts.filter(at_user=user).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries(req.user))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user.saves, parents=True) for entry in entries]
        }


class RepliesEndpoint:
    def fetch_entries(self, user):
        entries = Posts.filter(to_user=user).order_by('-id')
        return entries.prefetch_related(PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries(req.user))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user.saves) for entry in entries]
        }


class SavedEndpoint:
    def fetch_entries(self, user):
        saved_ids = Save.objects.filter(created_by=user).values('post__id')
        entries = Posts.filter(id__in=saved_ids).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries(req.user))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user.saves, parents=True) for entry in entries]
        }


class PeopleEndpoint:
    fields = [
        "username", "first_name", "last_name", "email",
        "description", "birthday", "location", "emoji", "link"
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
        qs = User.objects.filter(q)
        return qs.order_by('id') if terms else qs.order_by('-id')

    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, page = paginate(req, self.fetch_entries(terms), 24)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_user(entry) for entry in entries]
        }


class DiscoverEndpoint:
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
        entries, page = paginate(req, self.fetch_entries(terms))
        saves = req.user.saves if req.user else []
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, saves, parents=True) for entry in entries]
        }


class TrendingEndpoint:
    limit = 24

    def fetch_entries(self):
        sample = Post.objects.filter(parent=None).exclude(
            kids=None
        ).order_by('-id').values('id')[:self.limit]
        entries = Posts.filter(id__in=sample).order_by('-replies', '-id')
        return entries.prefetch_related(PFR)

    @before(auth_user)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries())
        saves = req.user.saves if req.user else []
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, saves, parents=True) for entry in entries]
        }


class MessagesEndpoint:
    def fetch_entries(self, req):
        last_ids = Chat.objects.filter(
            to_user=req.user
        ).values('created_by_id').annotate(last_id=Max('id')).values('last_id')
        entries = Chat.objects.filter(id__in=last_ids).order_by('-id')
        return entries.select_related('created_by')

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, page = paginate(req, self.fetch_entries(req))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_chat(entry) for entry in entries]
        }


class ChatEndpoint:
    def fetch_entries(self, req, member):
        entries = Chat.objects.filter(
            Q(created_by=req.user.id, to_user=member.id) | Q(created_by=member.id, to_user=req.user.id)
        ).order_by('-id')
        return entries.select_related('created_by', 'to_user')

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            raise HTTPNotFound
        entries, page = paginate(req, self.fetch_entries(req, member))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_chat(entry) for entry in entries]
        }


class NotificationsEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        resp.content_type = MEDIA_JSON
        resp.media = {
            'followers': req.user.notif_followers,
            'mentions': req.user.notif_mentions,
            'replies': req.user.notif_replies,
            'messages': req.user.notif_messages
        }


class DeleteEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        entry = Post.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        valid_ids = [
            entry.created_by_id, entry.parent.created_by_id
        ] if entry.parent_id else [entry.created_by_id]
        if req.user.id not in valid_ids:
            resp.media = {'status': 'not valid'}
            return
        entry.delete()
        resp.media = {'status': 'deleted'}


class SaveEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        entry = Post.objects.filter(id=id).exclude(created_by=req.user).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        Save.objects.get_or_create(
            created_at=utc_timestamp(),
            created_by=req.user,
            post=entry
        )
        resp.media = {'status': 'unsave'}


class UnsaveEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        entry = Post.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        Save.objects.filter(created_by=req.user, post=entry).delete()
        resp.media = {'status': 'save'}


class FollowEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Bond.objects.get_or_create(
            created_at=utc_timestamp(), created_by=req.user, to_user=member
        )
        resp.media = {'status': 'unfollow'}


class UnfollowEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Bond.objects.filter(created_by=req.user, to_user=member).delete()
        resp.media = {'status': 'follow'}


class UnsendEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        entry = Chat.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        if req.user.id != entry.created_by_id:
            resp.media = {'status': 'not valid'}
            return
        entry.delete()
        resp.media = {'status': 'unsent'}


class EraseEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        entry = Work.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        entry.delete()
        resp.media = {'status': 'erased'}
