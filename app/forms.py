from emoji import demojize, emojize
from unidecode import unidecode


def get_content(form, field="content"):
    value = form.getvalue(field, '')
    demojized = demojize(value)
    decoded = unidecode(demojized)
    words = [w.strip() for w in decoded.split()]
    return " ".join(words)


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    demojized = demojize(value)
    return emojize(demojized)


def get_name(form, field):
    value = form.getvalue(f'{field}_name', '')
    words = [w.strip().capitalize() for w in value.split()]
    return "-".join(words)
