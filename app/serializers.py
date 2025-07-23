from emoji import emojize
from app.filters import timeago
from app.utils import utc_timestamp


def build_user(user):
    data = {
        "username": user.username,
        "full_name": emojize(user.full_name)
    }
    return data


def build_entry(entry, parent=False):
    data = {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": build_user(entry.created_by),
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
    if parent:
        data['parent'] = build_entry(entry.parent) if entry.parent else {}
    if not entry.parent:
        data['kids'] = [build_entry(kid) for kid in entry.kids.all()]
    return data
