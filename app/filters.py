from datetime import date, datetime, timezone
from string import ascii_letters, digits

from tldextract import extract

from project.vars import LINKS


def enumerize(links):
    """Enumerate social links."""
    keys = sorted(links)  # eg. github
    holder = ""
    for key in keys[:-2]:
        holder += LINKS[key].format(links[key]) + ", "
    for index, key in enumerate(keys[-2:]):
        holder += LINKS[key].format(links[key])
        if not index and len(keys) > 1:
            holder += " and "
    return holder


def hostname(value):
    """Get hostname from an url."""
    subdomain, domain, suffix = extract(value)
    if subdomain in ['', 'www']:
        return f'{domain}.{suffix}'
    return f'{subdomain}.{domain}.{suffix}'


def age(birthday, delimiter="-"):
    """Age based on yyyy-mm-dd format."""
    delimiters = birthday.count(delimiter)
    if delimiters:
        integers = [int(v) for v in birthday.split(delimiter)]
        if len(integers) == 2:
            integers += [15]
        year, month, day = integers
        delta = datetime.now(timezone.utc).date() - date(year, month, day)
        return int(round(delta.days / 365.25))
    return datetime.now(timezone.utc).year - int(birthday)


def timeago(seconds):
    """Convert seconds to m, h, d, w, y."""
    milliseconds = round(seconds * 1000)
    seconds = round(seconds)
    days = seconds // (3600 * 24)
    years = days // 365.25
    weeks = (days - 365.25 * years) // 7
    days = days - 365.25 * years
    if not years and not days:
        if not seconds:
            return "%dms" % milliseconds
        if seconds < 60:
            return "%ds" % seconds
        if seconds < 3600:
            return "%dm" % (seconds // 60)
        return "%dh" % (seconds // 3600)
    if not years:
        if not weeks:
            return "%dd" % days
        return "%dw" % weeks
    if not weeks and not days:
        return "%dy" % years
    if not weeks:
        return "%dy, %dd" % (years, days)
    return "%dy, %dw" % (years, weeks)


def superscript(number):
    """Convert 1 to sup(1)."""
    text = str(number)
    ints = [8304, 185, 178, 179, 8308, 8309, 8310, 8311, 8312, 8313]
    for i, o in enumerate(ints):
        text = text.replace(str(i), chr(o))
    return text


def parser(text):
    """Convert plain text to HTML."""
    limits = digits + ascii_letters + "_"
    # unicode xml safe
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # replace &nbsp; (160) with space (32)
    text = text.replace(chr(160), chr(32))
    # split text in words and parse each
    words = []
    for word in text.split():
        # unwrap word
        endswith = ""
        startswith = ""
        if word.endswith(('.', ',', '!', '?', ':', ';')):
            endswith = word[-1:]
            word = word[:-1]
        if word.endswith((')', ']', '}', "'", '"')):
            endswith = word[-1:] + endswith
            word = word[:-1]
        if word.startswith(('(', '[', '{', "'", '"')):
            startswith = word[:1]
            word = word[1:]
        if word.endswith("'s"):
            endswith = word[-2:] + endswith
            word = word[:-2]
        # replace word
        if word.startswith(('http://', 'https://')):
            protocol, separator, address = word.partition('://')
            if address.startswith('www.'):
                address = address[4:]
            if address.endswith('/'):
                address = address[:-1]
            if len(address) > 21:
                address = address[:18] + '...'
            if address:
                word = f'<a href="{word}" rel="external">{address}</a>'
        elif word.startswith('@'):
            handle = word[1:]
            if handle and all(c in limits for c in handle):
                word = f'<a href="/{handle}" rel="author">@{handle}</a>'
        elif word.startswith('#'):
            handle = word[1:]
            if handle and all(c in limits for c in handle):
                word = f'<a href="/sub/{handle}" rel="tag">#{handle}</a>'
        # wrap word
        word = startswith + word + endswith
        words.append(word)
    return " ".join(words)
