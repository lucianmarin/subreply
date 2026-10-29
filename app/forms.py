from string import digits

from emoji import demojize
from unidecode import unidecode

from app.utils import ALNUM_CHARS, USERNAME_CHARS, unwrap
from project.vars import COUNTRIES


def get_content(form, field="content"):
    value = form.get(field, '')
    demojized = demojize(value)
    decoded = unidecode(demojized)
    return " ".join(decoded.split())


def get_emoji(form):
    value = form.get('emoji', '').strip()
    return demojize(value)


def get_location(form, delimiter=", "):
    location = form.get('location', '').strip()
    if delimiter in location:
        city, country = location.rsplit(delimiter, 1)
        country = COUNTRIES.get(country, country)
        return delimiter.join([city, country])
    return location


def get_name(form, field):
    value = form.get(f'{field}_name', '')
    return " ".join(value.split())


def get_metadata(text):
    hashtags, links, mentions = [], [], []
    for word in text.split():
        _, word, _ = unwrap(word)
        if word.startswith(('http://', 'https://')):
            protocol, separator, address = word.partition('://')
            if "." in address:
                links.append(word.lower())
        elif word.startswith('@'):
            handle = word[1:]
            if handle and all(c in USERNAME_CHARS for c in handle):
                mentions.append(handle.lower())
        elif word.startswith('#'):
            handle = word[1:]
            if handle and all(c in digits for c in handle):
                continue
            elif handle and all(c in ALNUM_CHARS for c in handle):
                hashtags.append(handle.lower())
    return hashtags, links, mentions
