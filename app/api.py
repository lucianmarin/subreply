from datetime import datetime
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
        entry = Comment.objects.filter(id=id, created_by=req.user).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        if entry.mentioned and not entry.seen_at:
            entry.mentioned.up_mentions()
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
            created_at=datetime.utcnow().timestamp(),
            created_by=req.user,
            to_comment=entry
        )
        req.user.up_saves()
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
        req.user.up_saves()
        resp.media = {'status': 'save'}


class PinEndpoint:
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
        if entry.pinned_by_id:
            resp.media = {'status': 'already pinned'}
            return
        Comment.objects.filter(pinned_by=req.user).update(pinned_by=None)
        entry.pinned_by = req.user
        entry.seen_at = .0
        entry.save(update_fields=['pinned_by', 'seen_at'])
        entry.created_by.up_pins()
        resp.media = {'status': 'unpin'}


class UnpinEndpoint:
    @before(auth_user)
    def on_post(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Comment.objects.filter(id=id, pinned_by=req.user).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        entry.created_by.up_pins()
        entry.pinned_by = None
        entry.save(update_fields=['pinned_by'])
        resp.media = {'status': 'pin'}
