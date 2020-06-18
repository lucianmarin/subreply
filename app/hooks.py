from falcon import HTTPFound

from app.models import User
from project.settings import F


def auth_user(req, resp, resource, params):
    token = req.cookies.get('identity', '')
    identity = F.decrypt(token.encode()).decode() if token else 0
    req.user = User.objects.filter(id=identity).first()
    if req.user:
        remote_addr = req.access_route[0]
        req.user.up_seen(remote_addr)


def login_required(req, resp, resource, params):
    if not req.user:
        raise HTTPFound('/login')
