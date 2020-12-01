import emoji

from unidecode import unidecode
from grapheme import graphemes


def get_content(form):
    value = form.getvalue('content', '')
    demojized = emoji.demojize(value)
    decoded = unidecode(demojized)
    words = [w.strip() for w in decoded.split()]
    return " ".join(words)


def get_emoji(form):
    value = form.getvalue('emoji', '').strip()
    demojized = emoji.demojize(value)
    listed = graphemes(emoji.emojize(demojized))
    chars = [c for c in listed if c in emoji.UNICODE_EMOJI]
    return "".join(chars)
