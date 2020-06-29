from datetime import datetime

from app.const import COUNTRIES


def country(code):
    return COUNTRIES.get(code, 'None')


def age(year):
    birthday = datetime(int(year), 7, 2).timestamp()
    now = datetime.utcnow().timestamp()
    seconds = 3600 * 24 * 365
    return round((now - birthday) / seconds)


def shortdate(timestamp):
    """Short time interval for a timestamp."""
    seconds = datetime.utcnow().timestamp() - timestamp
    milliseconds = round(seconds * 1000)
    seconds = round(seconds)
    days = seconds // (3600 * 24)
    years = days // 365
    weeks = (days - 365 * years) // 7
    days = days - 365 * years
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
    text = text.replace('9', chr(8313))
    return text


def parser(text):
    """Convert plain text to HTML."""
    limits = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    # unicode xml safe
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # replace &nbsp; (160) with space (32)
    text = text.replace(chr(160), chr(32))
    # split text in words and parse each
    words = text.split()
    for index in range(len(words)):
        word = words[index]
        # unwrap word
        endswith = ""
        startswith = ""
        if word.endswith(('.', ',', '!', '?', ':', ';')):
            endswith = word[-1:]
            word = word[:-1]
        if word.endswith(')'):
            endswith = word[-1:] + endswith
            word = word[:-1]
        if word.startswith('('):
            startswith = "("
            word = word[1:]
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
                word = '<a href="{0}" rel="external nofollow">{1}</a>'.format(word, address)
        elif word.startswith('@'):
            handle = word[1:]
            if handle and all(c in limits for c in handle):
                word = '<a href="/{0}" rel="author">@{0}</a>'.format(handle)
        elif word.startswith('#'):
            handle = word[1:]
            if handle and all(c in limits for c in handle):
                word = '<a href="/search/&#63;q=%23{0}" rel="tag">#{0}</a>'.format(handle)
        # wrap word
        words[index] = startswith + word + endswith
    return " ".join(words)
