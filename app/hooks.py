from falcon import HTTPFound, HTTPError

from app.models import User
from project.settings import FERNET


async def auth_user(req, resp, resource, params):
    token = req.headers.get('AUTHORIZATION', '').replace('Bearer ', '')
    token = token if token else req.cookies.get('identity', '')
    try:
        identity = FERNET.decrypt(token.encode()).decode() if token else 0
    except Exception as e:
        print(e)
        identity = 0
    req.user = await User.objects.filter(id=identity).afirst()
    if req.user:
        req.user.notif_followers = await req.user.followers.filter(seen_at=.0).acount()
        req.user.notif_mentions = await req.user.mentions.filter(mention_seen_at=.0).acount()
        req.user.notif_replies = await req.user.replies.filter(reply_seen_at=.0).acount()
        req.user.notif_messages = await req.user.received.filter(seen_at=.0).acount()
        req.user.follows = [f async for f in req.user.following.values_list('to_user_id', flat=True)]
        req.user.saves = [s async for s in req.user.saved.values_list('post_id', flat=True)]


async def login_required(req, resp, resource, params):
    if not req.user:
        raise HTTPFound('/login')


async def auth_required(req, resp, resource, params):
    if not req.user:
        raise HTTPError('Login required')
