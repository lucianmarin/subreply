from falcon import HTTPFound

from app.models import Request, User
from project.settings import F


def auth_user(req, resp, resource, params):
    try:
        token = req.cookies['identity']
        identity = F.decrypt(token.encode()).decode()
        remote_addr = req.access_route[0]
        req.user = User.objects.get(id=identity)
        req.user.up_seen(remote_addr)
        if req.user.id == 1:
            req.user.requests = Request.objects.count()
    except Exception as e:
        print('auth', e)
        req.user = User.objects.none()


def login_required(req, resp, resource, params):
    if not req.user:
        raise HTTPFound('/login')
