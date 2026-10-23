from emoji import emojize
from app.filters import timeago
from app.utils import utc_timestamp


def build_user(user, req_user):
    follows = req_user.follows if req_user else []
    return {
        "followed": user.id in follows,
        "username": user.username,
        "full_name": emojize(user.full_name),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "created_at": user.created_at,
        "emoji": user.emoji,
        "birthday": user.birthday,
        "location": user.location,
        "link": user.link,
        "description": user.description,
        "phone": user.phone,
        "social": user.social,
    }


def build_entry(entry, req_user, has_parent=False, has_kids=False):
    saves = req_user.saves if req_user else []
    data = {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by, req_user),
        "saved": entry.id in saves,
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
    if has_parent:
        data['parent'] = build_entry(entry.parent, req_user) if entry.parent else None
    if has_kids:
        data['kids'] = [build_entry(kid, req_user) for kid in entry.kids.all()]
    return data


def build_chat(entry, req_user):
    return {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by, req_user),
        "to_user": build_user(entry.to_user, req_user),
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
