from emoji import emojize
from app.filters import timeago
from app.utils import utc_timestamp


def build_user(user):
    return {
        "username": user.username,
        "full_name": emojize(user.full_name)
    }


def build_entry(entry, saves, parents=False):
    data = {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by),
        "saved": entry.id in saves,
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
    if parents:
        data['parent'] = build_entry(entry.parent, saves) if entry.parent else None
    if not entry.parent:
        data['kids'] = [build_entry(kid, saves) for kid in entry.kids.all()]
    return data


def build_chat(entry):
    return {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by),
        "to_user": build_user(entry.to_user),
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
