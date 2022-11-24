from datetime import date, datetime, timezone

from tldextract import extract


def hostname(value):
    """Get hostname from an url."""
    subdomain, domain, suffix = extract(value)
    if subdomain in ['', 'www']:
        return f'{domain}.{suffix}'
    return f'{subdomain}.{domain}.{suffix}'


def age(birthday, delimiter="-"):
    """Age based on yyyy-mm-dd format."""
    if birthday.count(delimiter):
        integers = [int(v) for v in birthday.split(delimiter)]
        integers += [15] if len(integers) == 2 else []
        year, month, day = integers
        delta = datetime.now(timezone.utc).date() - date(year, month, day)
        years = round(delta.days / 365.25, 1)
        return int(years) if years.is_integer() else years
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
        elif seconds < 60:
            return "%ds" % seconds
        elif seconds < 3600:
            return "%dm" % (seconds // 60)
        else:
            return "%dh" % (seconds // 3600)
    elif not years:
        if not weeks:
            return "%dd" % days
        else:
            return "%dw" % weeks
    else:
        if not weeks and not days:
            return "%dy" % years
        elif not weeks:
            return "%dy, %dd" % (years, days)
        else:
            return "%dy, %dw" % (years, weeks)


def superscript(number):
    """Convert 1 to sup(1)."""
    text = str(number)
    text = text.replace('0', chr(8304))
    text = text.replace('1', chr(185))
    text = text.replace('2', chr(178))
    text = text.replace('3', chr(179))
    text = text.replace('4', chr(8308))
    text = text.replace('5', chr(8309))
    text = text.replace('6', chr(8310))
    text = text.replace('7', chr(8311))
    text = text.replace('8', chr(8312))
    return text.replace('9', chr(8313))


def parser(text):
    """Convert plain text to HTML."""
    numbers = "0123456789"
    base36 = numbers + "abcdefghijklmnopqrstuvwxyz"
    limits = base36 + "ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
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
            elif '/' in handle:
                username, slash, reply = handle.partition('/')
                word = f'<a href="/{username}" rel="author">@{username}</a>/<a href="/{username}/{reply}" rel="bookmark">{reply}</a>'
        elif word.startswith('#'):
            handle = word[1:]
            if handle and all(c in numbers for c in handle):
                word = f'<a href="/reply/{handle}" rel="bookmark">#{handle}</a>'
            elif handle and all(c in limits for c in handle):
                word = f'<a href="/discover?q={handle}" rel="tag">#{handle}</a>'
        # wrap word
        word = startswith + word + endswith
        words.append(word)
    return " ".join(words)
