from falcon import HTTPFound

from app.models import User
from project.settings import FERNET


def auth_user(req, resp, resource, params):
    token = req.cookies.get('identity', '')
    try:
        identity = FERNET.decrypt(token.encode()).decode() if token else 0
    except Exception as e:
        print(e)
        identity = 0
    req.user = User.objects.filter(id=identity).first()


def login_required(req, resp, resource, params):
    if not req.user:
        raise HTTPFound('/login')
