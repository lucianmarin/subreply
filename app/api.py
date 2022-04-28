from falcon.constants import MEDIA_JSON
from falcon.hooks import before

from app.helpers import utc_timestamp
from app.hooks import auth_user
from app.models import Comment, Message, Relation, Save, User


class UnsendEndpoint:
    @before(auth_user)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Message.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        if entry.created_by_id != req.user.id:
            resp.media = {'status': 'not valid'}
            return
        entry.delete()
        resp.media = {'status': 'unsent'}


class DeleteEndpoint:
    @before(auth_user)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Comment.objects.filter(id=id).first()
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
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Comment.objects.filter(id=id).exclude(created_by=req.user).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        Save.objects.get_or_create(
            created_at=utc_timestamp(),
            created_by=req.user,
            to_comment=entry
        )
        resp.media = {'status': 'unsave'}


class UnsaveEndpoint:
    @before(auth_user)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Comment.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        Save.objects.filter(created_by=req.user, to_comment=entry).delete()
        resp.media = {'status': 'save'}


class FollowEndpoint:
    @before(auth_user)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Relation.objects.get_or_create(
            created_at=utc_timestamp(), created_by=req.user, to_user=member
        )
        resp.media = {'status': 'unfollow'}


class UnfollowEndpoint:
    @before(auth_user)
    def on_post(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Relation.objects.filter(created_by=req.user, to_user=member).delete()
        resp.media = {'status': 'follow'}
