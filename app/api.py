from emoji import demojize
from falcon import HTTPNotFound
from falcon.hooks import before
from falcon.constants import MEDIA_JSON
from django.db.models import Q

from app.forms import get_content
from app.hooks import auth_required, auth_user
from app.models import Bond, Chat, Post, Save, User
from app.resources import (
    DetailsResource, DiscoverResource, EditResource, FeedResource,
    FollowersResource, FollowingResource, LoginResource, MemberResource,
    MentionsResource, MessageResource, MessagesResource, PeopleResource,
    Posts, PPFR, ProfileResource, RegisterResource, RepliesResource,
    ReplyResource, SavedResource, TrendingResource, paginate
)
from app.serializers import build_entry, build_user, build_chat
from app.utils import utc_timestamp


class LoginEndpoint(LoginResource):
    @before(auth_user)
    def on_post(self, req, resp):
        form = req.get_media()
        errors, user = self.authenticate_user(form)
        resp.content_type = MEDIA_JSON
        if errors:
            resp.media = {'errors': errors}
        else:
            resp.media = {
                "token": self.build_token(user),
                "user": build_user(user, user)
            }


class RegisterEndpoint(RegisterResource):
    @before(auth_user)
    def on_post(self, req, resp):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        f = self.parse_form(form)
        errors = self.validate_registration(f)
        if errors:
            resp.media = {'errors': errors}
        else:
            user = self.create_user(f)
            resp.media = {
                "token": self.build_token(user),
                "user": build_user(user, user)
            }


class ProfileEndpoint(ProfileResource):
    @before(auth_user)
    @before(auth_required)
    def on_patch(self, req, resp):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        f = self.parse_form(form)
        errors = self.validate_profile(f, req.user)
        if errors:
            resp.media = {'errors': errors}
        else:
            self.update_user(req.user, f)
            resp.media = {'user': build_user(req.user, req.user)}


class DetailsEndpoint(DetailsResource):
    @before(auth_user)
    @before(auth_required)
    def on_patch(self, req, resp):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        s, p = self.parse_form(form)
        errors = self.validate_details(s, p)
        if errors:
            resp.media = {'errors': errors}
        else:
            self.update_user(req.user, s, p)
            resp.media = {'user': build_user(req.user, req.user)}


class ThreadEndpoint(FeedResource):
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        content = get_content(form)
        errors = self.validate_entry(content, req.user)
        if errors:
            resp.media = {'errors': errors}
        else:
            th = self.create_entry(content, req.user)
            resp.media = build_entry(th, req.user, has_parent=True)


class SendEndpoint(MessageResource):
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        member = self.fetch_member(username)
        content = get_content(form)
        errors = self.validate_message(content, req.user, member)
        if errors:
            resp.media = {'errors': errors}
        else:
            msg = self.create_entry(req.user, member, content)
            resp.media = build_chat(msg, req.user)


class FeedEndpoint(FeedResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        resp.content_type = MEDIA_JSON
        entries, _, page = paginate(req, self.fetch_entries(req.user))
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_parent=True, has_kids=True) for entry in entries]
        }


class ReplyEndpoint(ReplyResource):
    @before(auth_user)
    def on_get(self, req, resp, id):
        parent = Posts.filter(id=id).first()
        if not parent:
            raise HTTPNotFound
        duplicate = self.has_duplicate(parent, req.user)
        ancestors = self.fetch_ancestors(parent)
        entries = self.fetch_entries(parent)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "entry": build_entry(parent, req.user),
            "ancestors": [build_entry(entry, req.user) for entry in ancestors],
            "kids": [build_entry(entry, req.user, has_kids=True) for entry in entries],
            "duplicate": duplicate
        }

    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        parent = Posts.filter(id=id).select_related('parent').first()
        if not parent:
            raise HTTPNotFound
        form = req.get_media()
        content = get_content(form)
        errors = self.validate_entry(parent, content, req.user)
        if errors:
            resp.media = {'errors': errors}
        else:
            if existing := Posts.filter(parent=parent, created_by=req.user).prefetch_related(PPFR).first():
                resp.media = build_entry(existing, req.user, has_parent=True)
                return
            re = self.create_entry(parent, content, req.user)
            resp.media = build_entry(re, req.user, has_parent=True)


class MemberEndpoint(MemberResource):
    @before(auth_user)
    def on_get_details(self, req, resp, username):
        member = self.fetch_member(username)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "member": build_user(member, req.user),
        }

    @before(auth_user)
    def on_get_posts(self, req, resp, username):
        member = self.fetch_member(username)
        entries, _, page = paginate(req, self.fetch_entries(member))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_parent=True, has_kids=True) for entry in entries]
        }


class FollowingEndpoint(FollowingResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries(req.user), 24)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_user(entry.to_user, req.user, timestamp=entry.created_at) for entry in entries]
        }


class FollowersEndpoint(FollowersResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries(req.user), 24)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_user(entry.created_by, req.user, timestamp=entry.created_at) for entry in entries]
        }
        if req.user.notif_followers:
            self.clear_followers(req.user)


class MentionsEndpoint(MentionsResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries(req.user))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_parent=True, has_kids=True) for entry in entries]
        }
        if req.user.notif_mentions:
            self.clear_mentions(req.user)


class RepliesEndpoint(RepliesResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries(req.user))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_parent=True) for entry in entries]
        }
        if req.user.notif_replies:
            self.clear_replies(req.user)


class SavedEndpoint(SavedResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries(req.user))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_parent=True, has_kids=True) for entry in entries]
        }


class PeopleEndpoint(PeopleResource):
    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, _, page = paginate(req, self.fetch_entries(terms), 24)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_user(entry, req.user) for entry in entries]
        }


class DiscoverEndpoint(DiscoverResource):
    @before(auth_user)
    def on_get(self, req, resp):
        q = demojize(req.params.get('q', '').strip())
        terms = [t.strip() for t in q.split() if t.strip()]
        entries, _, page = paginate(req, self.fetch_entries(terms))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_parent=True, has_kids=True) for entry in entries]
        }


class TrendingEndpoint(TrendingResource):
    @before(auth_user)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries())
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, req.user, has_kids=True) for entry in entries]
        }


class MessagesEndpoint(MessagesResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        entries, _, page = paginate(req, self.fetch_entries(req))
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "entries": [build_chat(entry, req.user) for entry in entries]
        }


class MessageEndpoint(MessageResource):
    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp, username):
        member = self.fetch_member(username)
        entries, _, page = paginate(req, self.fetch_entries(req, member))
        blocked = self.is_blocked(req.user, member)
        resp.content_type = MEDIA_JSON
        resp.media = {
            "page": page,
            "blocked": blocked,
            "entries": [build_chat(entry, req.user) for entry in entries]
        }
        self.clear_messages(req, member)


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

# ACTIONS

class EditEndpoint(EditResource):
    @before(auth_user)
    @before(auth_required)
    def on_patch(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        entry = self.fetch_entry(id)
        if not entry:
            resp.media = {'status': 'not found'}
            return
        # only author can edit and entries with replies cannot be edited
        if req.user.id != entry.created_by_id or entry.replies:
            resp.media = {'status': 'not valid'}
            return

        form = req.get_media()
        content = get_content(form)
        errors = self.validate_entry(entry, content, req.user)
        if errors:
            resp.media = {'errors': errors}
            return

        self.update_entry(entry, content)
        resp.media = build_entry(entry, req.user, has_parent=True)


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
            entry.created_by_id, entry.to_user_id
        ] if entry.parent_id else [entry.created_by_id]
        if req.user.id not in valid_ids:
            resp.media = {'status': 'not valid'}
            return
        if entry.replies:
            resp.media = {'status': 'not valid'}
            return
        entry.subtract_replies()
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
        _, is_new = Save.objects.get_or_create(
            created_by=req.user,
            post=entry,
            defaults={'created_at': utc_timestamp()}
        )
        resp.media = {'status': 'unsave'}


class UnsaveEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not Post.objects.filter(id=id).exists():
            resp.media = {'status': 'not found'}
            return
        Save.objects.filter(created_by=req.user, post_id=id).delete()
        resp.media = {'status': 'save'}


class FollowEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        username = username.lower()
        member = User.objects.filter(username=username).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        _, is_new = Bond.objects.get_or_create(
            created_by=req.user, to_user=member,
            defaults={'created_at': utc_timestamp()}
        )
        resp.media = {'status': 'unfollow'}


class UnfollowEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        username = username.lower()
        member = User.objects.filter(username=username).first()
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


class ClearoutEndpoint:
    @before(auth_user)
    @before(auth_required)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        username = username.lower()
        member = User.objects.filter(username=username).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Chat.objects.filter(
            Q(created_by=req.user.id, to_user=member.id) |
            Q(created_by=member.id, to_user=req.user.id)
        ).delete()
        resp.media = {'status': 'cleared'}
