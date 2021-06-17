from emoji import demojize, emojize
from unidecode import unidecode


def get_content(form, t="content"):
    value = form.getvalue(t, '')
    demojized = demojize(value)
    decoded = unidecode(demojized)
    words = [w.strip() for w in decoded.split()]
    return " ".join(words)


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    demojized = demojize(value)
    return emojize(demojized)


def get_name(form, t):
    value = form.getvalue(f'{t}_name', '')
    words = "".join([p.strip() for p in value.split()])
    return "-".join([w.capitalize() for w in words.split("-")])
