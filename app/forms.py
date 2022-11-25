from emoji import demojize
from unidecode import unidecode


def get_content(form, field="content"):
    value = form.getvalue(field, '')
    demojized = demojize(value)
    decoded = unidecode(demojized)
    return " ".join(w.strip() for w in decoded.split())


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    return demojize(value)


def get_name(form, field):
    value = form.getvalue(f'{field}_name', '')
    return "-".join(w.strip().capitalize() for w in value.split())
