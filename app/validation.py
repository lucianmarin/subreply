from datetime import date
from string import ascii_letters, digits

from django.db.models import Q
from dns.resolver import query as dns_query
from emoji import EMOJI_DATA, emoji_count
from phonenumbers import is_possible_number, is_valid_number, parse

from app.forms import get_metadata
from app.models import Post, User
from app.utils import has_repetitions, verify_hash
from project.vars import INVALID, MAX_YEAR, MIN_YEAR, CITIES, LATIN



def valid_hashtag(value):
    limits = digits + ascii_letters
    if not value:
        return "Value cannot be empty"
    elif len(value) > 15:
        return "Hashtag can't be longer than 15 characters"
    elif all(c in digits for c in value):
        return "Hashtag contains only digits"
    elif not all(c in limits for c in value):
        return "Hashtag can be only alphanumeric"
    elif has_repetitions(value):
        return "Hashtag contains repeating characters"


async def valid_content(value, user, limit=640):
    hashtags, links, mentions = get_metadata(value)
    if len(value) > limit:
        return f"Share fewer than {limit} characters"
    elif len(value) != len(value.encode()):
        return "Only ASCII characters are allowed"
    elif len(mentions) > 1:
        return "Mention a single member"
    elif len(links) > 1:
        return "Link a single address"
    elif len(hashtags) > 1:
        return "Use a single hashtag"
    elif hashtags:
        hashtag = hashtags[0]
        if hashtag == value.lower()[1:]:
            return "Share more than a hashtag"
        return valid_hashtag(hashtag)
    elif links:
        link = links[0]
        if len(link) > 240:
            return "Link can't be longer than 240 characters"
        elif link == value.lower():
            return "Share more than a link"
        elif link.startswith(('http://subreply.com', 'https://subreply.com')):
            return "Share a hashtag, a mention or a reply"
    elif mentions:
        mention = mentions[0]
        if user and mention == user.username:
            return "Don't mention yourself"
        elif mention == value.lower()[1:]:
            return "Share more than a mention"
        elif not await User.objects.filter(username=mention).aexists():
            return "@{0} account doesn't exists".format(mention)


async def valid_thread(value):
    """Duplicate topic against old topics."""
    threads = [t async for t in Post.objects.filter(
        parent=None
    ).select_related('created_by').order_by('-id')[:32]]
    duplicates = [t for t in threads if t.content.lower() == value.lower()]
    if duplicates:
        duplicate = duplicates[0]
        err = 'Thread #{0} started by @{1}'
        return err.format(duplicate.id, duplicate.created_by)


async def valid_reply(parent, user, value, mentions):
    """Duplicate reply against replies for topic including topic."""
    ancestors = [a async for a in parent.ancestors.values_list('id', flat=True)]
    top_id = min(ancestors) if ancestors else parent.id
    duplicate = await Post.objects.filter(
        (Q(ancestors=top_id) | Q(id=top_id)) & Q(content__iexact=value)
    ).select_related('created_by').afirst()
    if duplicate:
        err = 'Duplicate of #{0} by @{1}'
        return err.format(duplicate.id, duplicate.created_by)
    elif parent.created_by_id == user.id:
        return "Don't reply to yourself"
    elif mentions and mentions[0] == parent.created_by.username:
        return "Don't mention the author"


async def authentication(username, password):
    errors = {}
    title = "Email" if "@" in username else "Username"
    if "@" in username:
        user = await User.objects.filter(email=username).afirst()
    else:
        user = await User.objects.filter(username=username).afirst()
    if not user:
        errors['username'] = "{0} doesn't exist".format(title)
    elif not verify_hash(password, user.password):
        errors['password'] = "Password doesn't match"
    return errors, user


async def valid_username(value, user_id=0):
    limits = digits + ascii_letters + "_"
    if not value:
        return "Username can't be blank"
    elif len(value) > 15:
        return "Username can't be longer than 15 characters"
    elif not all(c in limits for c in value):
        return "Username can be only alphanumeric"
    elif has_repetitions(value):
        return "Username contains repeating characters"
    elif "__" in value:
        return "Username contains consecutive underscores"
    elif value in INVALID and user_id != 1:
        return "Username is invalid"
    elif await User.objects.filter(username=value).exclude(id=user_id).aexists():
        return "Username is already taken"


def valid_handle(value):
    limits = digits + ascii_letters + "_.-"
    if len(value) > 15:
        return "Handle can't be longer than 15 characters"
    elif not all(c in limits for c in value):
        return "Handle can be only alphanumeric"


def valid_id(value):
    if len(value) > 15:
        return "ID can't be longer than 15 characters"
    elif not all(c in digits for c in value):
        return "ID can be only numeric"


def valid_first_name(value):
    if not value:
        return "First name can't be blank"
    elif len(value) == 1:
        return "First name is just too short"
    elif len(value) > 15:
        return "First name can't be longer than 15 characters"
    elif emoji_count(value):
        return "First name contains emoji"
    elif has_repetitions(value):
        return "First name contains repeating characters"
    elif not all(c in LATIN for c in value):
        return "First name should use Latin characters"


def valid_last_name(value):
    if len(value) > 15:
        return "Last name can't be longer than 15 characters"
    elif emoji_count(value):
        return "Last name contains emoji"
    elif value and has_repetitions(value):
        return "Last name contains repeating characters"
    elif not all(c in LATIN for c in value):
        return "First name should use Latin characters"


async def valid_full_name(emoji, first_name, last_name, user_id=0):
    if await User.objects.filter(
        emoji=emoji, first_name=first_name, last_name=last_name
    ).exclude(id=user_id).aexists():
        return "Emoji and names combination is taken"
    elif first_name == last_name:
        return "First and last names should be different"


async def valid_email(value, user_id=0):
    if not value:
        return "Email can't be blank"
    elif len(value) > 120:
        return "Email can't be longer than 120 characters"
    elif len(value) != len(value.encode()):
        return "Email should use ASCII characters"
    elif "@" not in value:
        return "Email isn't a valid address"
    elif await User.objects.filter(email=value).exclude(id=user_id).aexists():
        return "Email is used by someone else"
    else:
        handle, domain = value.split('@', 1)
        try:
            has_mx = bool(dns_query(domain, 'MX'))
        except Exception:
            has_mx = False
        if not has_mx:
            return "Email can't be sent to this address"


async def valid_description(value, user_id=0):
    if value:
        user = await User.objects.filter(id=user_id).afirst()
        return await valid_content(value, user, limit=240)


async def valid_link(value, user_id=0):
    if value:
        duplicate = await User.objects.filter(link=value).exclude(id=user_id).afirst()
        if len(value) > 240:
            return "Link can't be longer than 240 characters"
        elif len(value) != len(value.encode()):
            return "Link should use ASCII characters"
        elif not value.startswith(('http://', 'https://')):
            return "Link hasn't a valid http(s) address"
        elif duplicate:
            return f'Link is used by @{duplicate}'


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
                except Exception:
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


def valid_date(value, delimiter="-"):
    if value:
        CUR_YEAR = date.today().year
        CUR_MONTH = date.today().month
        years = [str(y) for y in range(MIN_YEAR, CUR_YEAR + 1)]
        zeroes = [str(z).zfill(2) for z in range(1, 10)]
        months = zeroes + [str(m) for m in range(10, 13)]
        if value.count(delimiter) != 1:
            return "Date has an invalid format"
        elif len(value) > 7:
            return "Date is too long"
        elif value.count(delimiter) == 1:
            year, month = value.split(delimiter)
            if year not in years:
                return "Year is not between {0}-{1}".format(MIN_YEAR, CUR_YEAR)
            elif month not in months:
                return "Month is not between 01-12"
            elif year == str(CUR_YEAR) and int(month) > CUR_MONTH:
                return "Date is in the future"


def changing(user, current, password1, password2):
    errors = {}
    if not verify_hash(current, user.password):
        errors['current'] = "Password doesn't match"
    errors['password'] = valid_password(password1, password2)
    return {k: v for k, v in errors.items() if v}


async def profiling(f, user_id):
    errors = {}
    errors['username'] = await valid_username(f['username'], user_id=user_id)
    errors['email'] = await valid_email(f['email'], user_id=user_id)
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = await valid_full_name(
        f['emoji'], f['first_name'], f['last_name'], user_id=user_id
    )
    errors['emoji'] = valid_emoji(f['emoji'])
    errors['birthday'] = valid_birthday(f['birthday'])
    errors['location'] = valid_location(f['location'])
    errors['link'] = await valid_link(f['link'], user_id=user_id)
    errors['description'] = await valid_description(
        f['description'], user_id=user_id
    )
    return {k: v for k, v in errors.items() if v}


async def registration(f):
    errors = {}
    errors['username'] = await valid_username(f['username'])
    errors['email'] = await valid_email(f['email'])
    errors['password'] = valid_password(f['password1'], f['password2'])
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = await valid_full_name(
        f['emoji'], f['first_name'], f['last_name']
    )
    errors['emoji'] = valid_emoji(f['emoji'])
    errors['birthday'] = valid_birthday(f['birthday'])
    errors['location'] = valid_location(f['location'])
    return {k: v for k, v in errors.items() if v}
