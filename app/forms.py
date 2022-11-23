from emoji import demojize
from unidecode import unidecode
from app.helpers import to_metadata


def get_content(form, field="content"):
    value = form.getvalue(field, '')
    demojized = demojize(value)
    decoded = unidecode(demojized)
    text = " ".join(w.strip() for w in decoded.split())
    return to_metadata(text)


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    return demojize(value)


def get_name(form, field):
    value = form.getvalue(f'{field}_name', '')
    return "-".join(w.strip().capitalize() for w in value.split())
