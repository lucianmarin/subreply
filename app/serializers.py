from emoji import emojize
from app.filters import timeago
from app.utils import utc_timestamp


def build_user(user, req_user, timestamp=None):
    is_other = req_user and user.id != req_user.id
    follows = req_user.following_set if is_other else ()
    followers = req_user.followers_set if is_other else ()
    data = {
        "followed": user.id in follows,
        "follows": user.id in followers,
        "username": user.username,
        "full_name": emojize(user.full_name),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "created_at": user.created_at,
        "seen_at": user.seen_at,
        "donated": user.donated,
        "timestamp": timeago(utc_timestamp() - (timestamp if timestamp is not None else user.seen_at)),
        "emoji": emojize(user.emoji),
        "birthday": user.birthday,
        "location": user.location,
        "link": user.link,
        "description": user.description,
        "phone": user.phone,
        "social": user.social,
    }
    if req_user and user.id == req_user.id:
        data["email"] = user.email
    return data


def build_entry(entry, req_user, has_parent=False, has_kids=False):
    is_other = req_user and entry.created_by_id != req_user.id
    saves = req_user.saves_set if is_other else ()
    data = {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by, req_user),
        "saved": entry.id in saves,
        "edited": bool(entry.edited_at),
        "replies": entry.replies,
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
    if has_parent:
        data['parent'] = build_entry(entry.parent, req_user) if entry.parent else None
    if has_kids:
        data['kids'] = [build_entry(kid, req_user) for kid in entry.kids.all()]
    return data


def build_chat(entry, req_user):
    to_user = req_user if entry.to_user_id == req_user.id else entry.to_user
    return {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by, req_user),
        "to_user": build_user(to_user, req_user),
        "seen": bool(entry.seen_at),
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
