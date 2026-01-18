from emoji import emojize
from app.models import User
from app.filters import timeago
from app.utils import utc_timestamp


async def build_user(user_id):
    user = await User.objects.aget(id=user_id)
    return {
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


async def build_entry(entry, saves, parents=False):
    data = {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": await build_user(entry.created_by_id),
        "saved": entry.id in saves,
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
    if parents:
        data['parent'] = await build_entry(entry.parent, saves) if entry.parent else None
    data['kids'] = [await build_entry(kid, saves) async for kid in entry.kids.all()]
    return data


async def build_chat(entry):
    return {
        "id": entry.id,
        "content": emojize(entry.content),
        "created_by": await build_user(entry.created_by_id),
        "to_user": await build_user(entry.to_user_id),
        "timestamp": timeago(utc_timestamp() - entry.created_at)
    }
