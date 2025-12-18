from base64 import b64encode
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from random import choice
from string import ascii_letters, ascii_lowercase, digits


def has_repetitions(word, n=3):
    return any(char * n in word for char in word)


def utc_timestamp():
    return datetime.now(timezone.utc).timestamp()


def generate_salt(length=12):
    chars = digits + ascii_letters
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
    alphabet, base36 = digits + ascii_lowercase, ""
    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36
    return base36 or alphabet[0]


def base36decode(number):
    return int(number, 36)
