def build_user(user):
    data = {
        "id": user.id,
        "created_at": user.created_at,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "emoji": user.emoji
    }
    return data


def build_entry(entry, parent=False):
    data = {
        "id": entry.id,
        "content": entry.content,
        "created_by": build_user(entry.created_by)
    }
    if parent:
        data['parent'] = build_entry(entry.parent) if entry.parent else {}
    return data
