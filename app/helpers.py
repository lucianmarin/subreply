import secrets
from base64 import b64encode
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from random import choice


def has_repetions(word, n=3):
    for char in word:
        if char * n in word:
            return True
    return False


def utc_timestamp():
    return datetime.now(timezone.utc).timestamp()


def generate_passphrase(n=4):
    with open('/usr/share/dict/words') as f:
        words = [word.strip() for word in f]
        return ' '.join(secrets.choice(words) for i in range(n))


def parse_metadata(text):
    limits = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    words = text.split()
    hashtags = []
    links = []
    mentions = []
    for word in words:
        if word.endswith(('.', ',', '!', '?', ':', ';')):
            word = word[:-1]
        if word.endswith(')'):
            word = word[:-1]
        if word.startswith('('):
            word = word[1:]
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
            if handle and all(c in limits for c in handle):
                hashtags.append(handle)
    return mentions, links, hashtags


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
