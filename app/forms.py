from emoji import demojize, emojize
from unidecode import unidecode


def get_content(form, t="content"):
    value = form.getvalue(t, '')
    decoded = unidecode(value)
    words = [w.strip() for w in decoded.split()]
    return " ".join(words)


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    demojized = demojize(value)
    return emojize(demojized)


def get_name(form, t):
    value = form.getvalue(f'{t}_name', '')
    words = [w.strip().capitalize() for w in value.split()]
    return "-".join(words)
