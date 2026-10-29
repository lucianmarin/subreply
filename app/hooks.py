from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from falcon import HTTPFound, HTTPUnauthorized

from app.models import Bond, Chat, Post, User
from project.settings import FERNET


def count_subquery(qs, field='to_user'):
    return Coalesce(
        Subquery(
            qs.values(field).annotate(c=Count('*')).values('c'),
            output_field=IntegerField()
        ),
        0
    )


Users = User.objects.annotate(
    notif_followers=count_subquery(Bond.objects.filter(to_user=OuterRef('pk'), seen_at=.0)),
    notif_mentions=count_subquery(Post.objects.filter(at_user=OuterRef('pk'), mention_seen_at=.0), 'at_user'),
    notif_replies=count_subquery(Post.objects.filter(to_user=OuterRef('pk'), reply_seen_at=.0)),
    notif_messages=count_subquery(Chat.objects.filter(to_user=OuterRef('pk'), seen_at=.0)),
)


def auth_user(req, resp, resource, params):
    token = req.headers.get('AUTHORIZATION', '').replace('Bearer ', '')
    token = token if token else req.cookies.get('identity', '')
    try:
        identity = FERNET.decrypt(token.encode()).decode() if token else 0
    except Exception as e:
        print(e)
        identity = 0
    req.user = Users.filter(id=identity).first() if identity else None
    if req.user:
        req.user.set_seen()


def login_required(req, resp, resource, params):
    if not req.user:
        raise HTTPFound('/login')


def auth_required(req, resp, resource, params):
    if not req.user:
        raise HTTPUnauthorized(description='Login required')
