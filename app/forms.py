from string import ascii_letters, digits

from emoji import demojize
from unidecode import unidecode

from project.vars import COUNTRIES


def get_content(form, field="content"):
    value = form.getvalue(field, '')
    demojized = demojize(value)
    decoded = unidecode(demojized)
    words = [word.strip() for word in decoded.split()]
    return " ".join(words)


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    return demojize(value)


def get_location(form, delimiter=", "):
    location = form.getvalue('location', '').strip()
    if delimiter in location:
        city, country = location.split(delimiter)
        country = COUNTRIES.get(country, country)
        return delimiter.join([city, country])
    return location


def get_name(form, field):
    value = form.getvalue(f'{field}_name', '')
    return "-".join(w.strip().capitalize() for w in value.split())


def get_metadata(text):
    limits = digits + ascii_letters + "_"
    hashtags, links, mentions = [], [], []
    for word in text.split():
        if word.endswith(('.', ',', '!', '?', ':', ';')):
            word = word[:-1]
        if word.endswith((')', ']', '}', "'", '"')):
            word = word[:-1]
        if word.startswith(('(', '[', '{', "'", '"')):
            word = word[1:]
        if word.endswith("'s"):
            word = word[:-2]
        if word.startswith(('http://', 'https://')):
            protocol, separator, address = word.partition('://')
            if "." in address:
                links.append(word.lower())
        if word.startswith('@'):
            handle = word[1:]
            if handle and all(c in limits for c in handle):
                mentions.append(handle.lower())
        if word.startswith('#'):
            handle = word[1:]
            if handle and all(c in digits for c in handle):
                continue
            elif handle and all(c in digits + ascii_letters for c in handle):
                hashtags.append(handle.lower())
    return hashtags, links, mentions
