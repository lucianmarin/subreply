from falcon import HTTPFound

from app.models import User
from project.settings import F


def auth_user(req, resp, resource, params):
    try:
        token = req.cookies['identity']
        identity = F.decrypt(token.encode()).decode()
        remote_addr = req.access_route[0]
        req.user = User.objects.get(id=identity)
        req.user.up_seen(remote_addr)
    except Exception as e:
        print('auth', e)
        req.user = User.objects.none()


def login_required(req, resp, resource, params):
    if not req.user:
        raise HTTPFound('/login')
