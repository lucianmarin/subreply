from falcon.constants import MEDIA_JSON
from falcon.hooks import before

from app.hooks import auth_user
from app.models import Bond, Post, Save, User, Text
from app.utils import utc_timestamp


class PostCallback:
    @before(auth_user)
    def on_post_delete(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
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

    @before(auth_user)
    def on_post_save(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
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

    @before(auth_user)
    def on_post_unsave(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Post.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        Save.objects.filter(created_by=req.user, post=entry).delete()
        resp.media = {'status': 'save'}


class BondCallback:
    @before(auth_user)
    def on_post_follow(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Bond.objects.get_or_create(
            created_at=utc_timestamp(), created_by=req.user, to_user=member
        )
        resp.media = {'status': 'unfollow'}


    @before(auth_user)
    def on_post_unfollow(self, req, resp, username):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        member = User.objects.filter(username=username.lower()).first()
        if not member:
            resp.media = {'status': 'not found'}
            return
        Bond.objects.filter(created_by=req.user, to_user=member).delete()
        resp.media = {'status': 'follow'}


class TextCallback:
    @before(auth_user)
    def on_post_unsend(self, req, resp, id):
        resp.content_type = MEDIA_JSON
        if not req.user:
            resp.media = {'status': 'not auth'}
            return
        entry = Text.objects.filter(id=id).first()
        if not entry:
            resp.media = {'status': 'not found'}
            return
        if req.user.id != entry.created_by_id:
            resp.media = {'status': 'not valid'}
            return
        entry.delete()
        resp.media = {'status': 'unsent'}
