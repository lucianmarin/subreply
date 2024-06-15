from datetime import date
from string import ascii_letters, ascii_uppercase, digits

from django.db.models import Q
from dns.resolver import query as dns_query
from emoji import EMOJI_DATA
from phonenumbers import is_possible_number, is_valid_number, parse
from requests import head

from app.forms import get_metadata
from app.models import Comment, User
from app.utils import has_repetions, verify_hash
from project.vars import INVALID, LATIN, MAX_YEAR, MIN_YEAR, CITIES


def valid_hashtag(value):
    limits = digits + ascii_letters
    if not value:
        return "Value cannot be empty"
    elif len(value) > 15:
        return "Hashtag is too long"
    elif all(c in digits for c in value):
        return "Hashtag contains only digits"
    elif not all(c in limits for c in value):
        return "Hashtag can be only alphanumeric"
    elif has_repetions(value):
        return "Hashtag contains repetions"
    elif value in INVALID:
        return "Hashtag is not valid"


def valid_content(value, user, limit=640):
    hashtags, links, mentions = get_metadata(value)
    if not value:
        return "Value cannot be emtpy"
    elif len(value) > limit:
        return f"Share fewer than {limit} characters"
    elif len(value) != len(value.encode()):
        return "Only ASCII characters are allowed"
    elif len(mentions) > 1:
        return "Mention a single member"
    elif len(links) > 1:
        return "Link a single address"
    elif len(hashtags) > 1:
        return "Hashtag a single space"
    elif hashtags:
        hashtag = hashtags[0].lower()
        if hashtag == value.lower()[1:]:
            return "Share more than a space"
        return valid_hashtag(hashtag)
    elif links:
        link = links[0].lower()
        if len(link) > 240:
            return "Link can't be longer than 120 characters"
        elif link == value.lower():
            return "Share more than a link"
        elif link.startswith(('http://subreply.com', 'https://subreply.com')):
            return "Share a @mention, a #space or a reply #id"
    elif mentions:
        mention = mentions[0].lower()
        if user and mention == user.username:
            return "Don't mention yourself"
        elif mention == value.lower()[1:]:
            return "Share more than a mention"
        elif not User.objects.filter(username=mention).exists():
            return "@{0} account doesn't exists".format(mention)


def valid_thread(value):
    """Duplicate topic against old topics."""
    threads = Comment.objects.filter(parent=None).order_by('-id')[:32]
    duplicates = [t for t in threads if t.content.lower() == value.lower()]
    if duplicates:
        duplicate = duplicates[0]
        err = 'Thread <a href="/reply/{1}">#{1}</a> started by <a href="/{0}">@{0}</a>'
        return err.format(duplicate.created_by, duplicate.id)


def valid_reply(parent, user, value, mentions):
    """Duplicate reply against replies for topic including topic."""
    ancestors = parent.ancestors.values_list('id', flat=True)
    top_id = min(ancestors) if ancestors else parent.id
    duplicate = Comment.objects.filter(
        (Q(ancestors=top_id) | Q(id=top_id)) & Q(content__iexact=value)
    ).first()
    if duplicate:
        err = 'Duplicate of <a href="/reply/{1}">#{1}</a> by <a href="/{0}">@{0}</a>'
        return err.format(duplicate.created_by, duplicate.id)
    elif parent.created_by_id == user.id:
        return "Don't reply to yourself"
    elif len(mentions) == 1 and mentions[0].lower() == parent.created_by.username:
        return "Don't mention the author"


def authentication(username, password):
    errors = {}
    title = "Email" if "@" in username else "Username"
    if "@" in username:
        user = User.objects.filter(email=username).first()
    else:
        user = User.objects.filter(username=username).first()
    if not user:
        errors['username'] = "{0} doesn't exist".format(title)
    elif not verify_hash(password, user.password):
        errors['password'] = "Password doesn't match"
    return errors, user


def valid_username(value, user_id=0):
    limits = digits + ascii_letters + "_"
    if not value:
        return "Username can't be blank"
    elif len(value) > 15:
        return "Username can't be longer than 15 characters"
    elif not all(c in limits for c in value):
        return "Username can be only alphanumeric"
    elif has_repetions(value):
        return "Username contains repeating characters"
    elif "__" in value:
        return "Username contains consecutive underscores"
    elif value in INVALID:
        return "Username is invalid"
    elif User.objects.filter(username=value).exclude(id=user_id).exists():
        return "Username is already taken"


def valid_handle(value):
    limits = digits + ascii_letters + "_-"
    if len(value) > 15:
        return "Handle can't be longer than 15 characters"
    elif not all(c in limits for c in value):
        return "Handle can be only alphanumeric"


def valid_id(value):
    if len(value) > 15:
        return "Handle can't be longer than 15 characters"
    elif not all(c in digits for c in value):
        return "ID can be only numeric"


def valid_first_name(value):
    if not value:
        return "First name can't be blank"
    elif len(value) > 15:
        return "First name can't be longer than 15 characters"
    elif len(value) == 1:
        return "First name is just too short"
    elif not all(c in LATIN for c in value):
        return "First name should use Latin characters"
    elif has_repetions(value):
        return "First name contains repeating characters"
    elif value.count('-') > 1 or value.startswith('-') or value.endswith('-'):
        return "Only one double-name is allowed"


def valid_last_name(value):
    if len(value) > 15:
        return "Last name can't be longer than 15 characters"
    elif not all(c in LATIN for c in value):
        return "Last name should use Latin characters"
    elif value and has_repetions(value):
        return "Last name contains repeating characters"
    elif value.count('-') > 1 or value.startswith('-') or value.endswith('-'):
        return "Only one double-name is allowed"


def valid_full_name(emoji, first_name, last_name, user_id=0):
    if User.objects.filter(
        emoji=emoji, first_name=first_name, last_name=last_name
    ).exclude(id=user_id).exists():
        return "Emoji and names combination is taken"
    elif first_name == last_name:
        return "First and last names should be different"


def valid_email(value, user_id=0):
    if not value:
        return "Email can't be blank"
    elif len(value) > 120:
        return "Email can't be longer than 120 characters"
    elif len(value) != len(value.encode()):
        return "Email should use ASCII characters"
    elif "@" not in value:
        return "Email isn't a valid address"
    elif User.objects.filter(email=value).exclude(id=user_id).exists():
        return "Email is used by someone else"
    else:
        handle, domain = value.split('@', 1)
        try:
            has_mx = bool(dns_query(domain, 'MX'))
        except Exception as e:
            has_mx = False
            print(e)
        if not has_mx:
            return "Email can't be sent to this address"


def valid_description(value, user_id=0):
    if value:
        user = User.objects.filter(id=user_id).first()
        return valid_content(value, user, limit=120)


def valid_website(value, user_id=0):
    if value:
        duplicate = User.objects.filter(website=value).exclude(id=user_id).first()
        if len(value) > 120:
            return "Website can't be longer than 120 characters"
        elif len(value) != len(value.encode()):
            return "Website should use ASCII characters"
        elif not value.startswith(('http://', 'https://')):
            return "Website hasn't a valid http(s) address"
        elif duplicate:
            return f'Website is used by <a href="/{duplicate}">@{duplicate}</a>'
        else:
            try:
                headers = head(value, allow_redirects=True, timeout=5).headers
            except Exception as e:
                headers = {}
                print(e)
            if 'text/html' not in headers.get('Content-Type', '').lower():
                return "Website isn't a valid HTML page"


def valid_password(value1, value2):
    if not value1 or not value2:
        return "Password can't be blank"
    elif value1 != value2:
        return "Password doesn't match"
    elif len(value1) < 8:
        return "Password is just too short"
    elif len(value1) != sum(len(p) for p in value1.split()):
        return "Password contains spaces"
    elif value1 == value1.lower():
        return "Password needs an uppercase letter"
    elif value1 == value1.upper():
        return "Password needs a lowercase letter"


def valid_birthday(value, delimiter="-"):
    if value:
        years = [str(y) for y in range(MIN_YEAR, MAX_YEAR + 1)]
        zeroes = [str(z).zfill(2) for z in range(1, 10)]
        months = [str(m) for m in range(1, 13)] + zeroes
        days = [str(d) for d in range(1, 32)] + zeroes
        if value.count(delimiter) > 2:
            return "Birthday has an invalid format"
        elif len(value) > 10:
            return "Birthday is too long"
        elif value.count(delimiter) == 2:
            year, month, day = value.split(delimiter)
            if year not in years:
                return "Year is not between {0}-{1}".format(MIN_YEAR, MAX_YEAR)
            elif month not in months:
                return "Month is not between 1-12"
            elif day not in days:
                return "Day is not between 1-31"
            else:
                try:
                    _ = date(int(year), int(month), int(day))
                except Exception as e:
                    print(e)
                    return "Birthday is invalid"
        elif value.count(delimiter):
            year, month = value.split(delimiter)
            if year not in years:
                return "Year is not between {0}-{1}".format(MIN_YEAR, MAX_YEAR)
            elif month not in months:
                return "Month is not between 1-12"
        elif value not in years:
            return "Year is not between {0}-{1}".format(MIN_YEAR, MAX_YEAR)


def valid_location(value, delimiter=", "):
    if value:
        if value.count(delimiter) > 1:
            return "City, Country or just Country"
        elif value.count(delimiter):
            city, country = value.split(delimiter)
            if country not in CITIES:
                return "Country is invalid"
            elif city not in CITIES[country]:
                return "City is invalid"
        elif value not in CITIES:
            return "Country is invalid"


def valid_emoji(value):
    codes = [v['en'] for v in EMOJI_DATA.values()]
    if value and value not in codes:
        return "Emoji is invalid"


def valid_phone(code, number):
    if not code and not number:
        return
    elif not code:
        return "Code is needed"
    elif not number:
        return "Number is needed"
    elif not code.startswith('+'):
        return "Code starts with +"
    elif len(code) < 2 and len(code) > 4:
        return "Code between +1 and +999"
    elif not code[1:].isdecimal():
        return "Code must be numeric"
    elif not number.isdecimal():
        return "Number must be numeric"
    else:
        phone = parse(code + number, None)
        if not is_possible_number(phone):
            return "Number is impossible"
        elif not is_valid_number(phone):
            return "Number is invalid"


def valid_wallet(coin, id):
    if not coin and not id:
        return
    elif not coin:
        return "Coin or currency is needed"
    elif not id:
        return "ID or IBAN is needed"
    elif len(coin) > 5:
        return "Coin or currency is too long"
    elif len(id) < 15 or len(id) > 95:
        return "ID or IBAN between 15 and 95"
    elif not all(c in ascii_uppercase for c in coin):
        return "Coin or currency must be in uppercase letters"
    elif not all(c in digits + ascii_letters for c in id):
        return "ID or IBAN must be only digits and letters"


def changing(user, current, password1, password2):
    errors = {}
    if not verify_hash(current, user.password):
        errors['current'] = "Password doesn't match"
    errors['password'] = valid_password(password1, password2)
    return {k: v for k, v in errors.items() if v}


def profiling(f, user_id):
    errors = {}
    errors['username'] = valid_username(f['username'], user_id=user_id)
    errors['email'] = valid_email(f['email'], user_id=user_id)
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = valid_full_name(
        f['emoji'], f['first_name'], f['last_name'], user_id=user_id
    )
    errors['emoji'] = valid_emoji(f['emoji'])
    errors['birthday'] = valid_birthday(f['birthday'])
    errors['location'] = valid_location(f['location'])
    errors['description'] = valid_description(
        f['description'], user_id=user_id
    )
    errors['website'] = valid_website(f['website'], user_id=user_id)
    return {k: v for k, v in errors.items() if v}


def registration(f):
    errors = {}
    errors['username'] = valid_username(f['username'])
    errors['email'] = valid_email(f['email'])
    errors['password'] = valid_password(f['password1'], f['password2'])
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = valid_full_name(
        f['emoji'], f['first_name'], f['last_name']
    )
    errors['emoji'] = valid_emoji(f['emoji'])
    errors['birthday'] = valid_birthday(f['birthday'])
    errors['location'] = valid_location(f['location'])
    return {k: v for k, v in errors.items() if v}
