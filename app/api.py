from datetime import datetime, timezone

from falcon.constants import MEDIA_JSON
from falcon.hooks import before

from app.hooks import auth_user
from app.models import Comment, Save


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
            created_at=datetime.now(timezone.utc).timestamp(),
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
