from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from falcon import HTTPFound, HTTPUnauthorized

from app.models import Bond, Chat, Post, Save, User
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
    following_ids=ArraySubquery(Bond.objects.filter(created_by=OuterRef('pk')).exclude(to_user=OuterRef('pk')).values('to_user_id')),
    followers_ids=ArraySubquery(Bond.objects.filter(to_user=OuterRef('pk')).exclude(created_by=OuterRef('pk')).values('created_by_id')),
    saves_ids=ArraySubquery(Save.objects.filter(created_by=OuterRef('pk')).values('post_id')),
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
