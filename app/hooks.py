from falcon import HTTPFound

from app.models import User
from project.settings import FERNET


def auth_user(req, resp, resource, params):  # noqa
    token = req.cookies.get('identity', '')
    try:
        identity = FERNET.decrypt(token.encode()).decode() if token else 0
    except Exception as e:
        print(e)
        identity = 0
    req.user = User.objects.filter(id=identity).first()
    if req.user:
        remote_addr = req.access_route[0]
        req.user.up_seen(remote_addr)


def login_required(req, resp, resource, params):  # noqa
    if not req.user:
        raise HTTPFound('/login')
