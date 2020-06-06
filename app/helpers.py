from base64 import b64encode
from hashlib import pbkdf2_hmac
from random import choice
from PIL import Image, ImageOps


def parse_metadata(text):
    limits = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
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


def make_hash(password):
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


def save_image(file, name, size=240):
    image = Image.open(file)
    try:
        exif = dict(image._getexif().items())
        orientation = exif.get(274, None)
        if orientation == 3:
            image = image.rotate(180, expand=True)
        elif orientation == 6:
            image = image.rotate(270, expand=True)
        elif orientation == 8:
            image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        pass
    image = image.convert('RGB')
    image = ImageOps.fit(image, (size, size), Image.LANCZOS, 0, (0.5, 0.5))
    image.save(name, 'JPEG', quality=80, subsampling=0, progressive=True)
