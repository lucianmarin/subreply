from base64 import b64encode
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from random import choice


def cleaner(value):
    return " ".join([w.strip() for w in value.split()])


def has_repetions(word, n=3):
    return any(char * n in word for char in word)


def utc_timestamp():
    return datetime.now(timezone.utc).timestamp()


def to_words(number):
    index = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    data = dict(enumerate(index))
    words = []
    for n in str(number):
        words.append(data[int(n)])
    return " ".join(words)


def parse_metadata(text):
    numbers = "0123456789"
    base36 = numbers + "abcdefghijklmnopqrstuvwxyz"
    limits = base36 + "ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    hashrefs, hashtags, links, mentions = [], [], [], []
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
                links.append(word)
        if word.startswith('@'):
            handle = word[1:]
            if handle and all(c in limits for c in handle):
                mentions.append(handle)
        if word.startswith('#'):
            handle = word[1:]
            if handle and all(c in numbers for c in handle):
                hashrefs.append(handle)
            elif handle and all(c in limits for c in handle):
                hashtags.append(handle)
    return hashrefs, hashtags, links, mentions


def generate_salt(length=12):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(choice(chars) for i in range(length))


def build_hash(password):
    salt = generate_salt()
    iterations = 55555
    dk = pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
    h = b64encode(dk).decode('ascii').strip()
    return "%s$%d$%s$%s" % ("pbkdf2_sha256", iterations, salt, h)


def verify_hash(password, hashed):
    algorithm, iters, salt, old_h = hashed.split('$')
    dk = pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iters))
    h = b64encode(dk).decode('ascii').strip()
    return h == old_h


def base36encode(number):
    alphabet, base36 = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36
    return base36 or alphabet[0]


def base36decode(number):
    return int(number, 36)
