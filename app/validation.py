from datetime import date

import emoji
import grapheme
import requests
from django.db.models import Q
from dns.resolver import query as dns_query
from user_agents import parse

from app.const import LATIN, MAX_YEAR, MIN_YEAR, WORLD
from app.helpers import has_repetions, parse_metadata, verify_hash
from app.models import Comment, User
from project.settings import INVALID, SLURS


def valid_content(value, user):
    mentions, links, hashtags = parse_metadata(value)
    if not value:
        return "Status can't be blank"
    elif len(value) > 480:
        return "Status can't be longer than 480 characters"
    elif len(value) != len(value.encode()):
        return "Only English alphabet allowed"
    elif len(mentions) > 1:
        return "Mention a single user"
    elif len(links) > 1:
        return "Link a single address"
    elif len(hashtags) > 1:
        return "Hashtag a single channel"
    elif hashtags and len(hashtags[0]) > 15:
        return "Hashtag can't be longer than 15 characters"
    elif links and len(links[0]) > 120:
        return "Link can't be longer than 120 characters"
    elif mentions:
        mention = mentions[0].lower()
        if mention == user.username:
            return "Can't mention yourself"
        elif not User.objects.filter(username=mention).exists():
            return "@{0} isn't an user".format(mention)


def valid_thread(value):
    """Duplicate topic against old topics."""
    threads = Comment.objects.filter(parent=None).order_by('-id')[:40]
    duplicates = [t for t in threads if t.content.lower() == value.lower()]
    if duplicates:
        duplicate = duplicates[0]
        return f'Thread started by <a href="/{duplicate.created_by}/{duplicate.base}">@{duplicate.created_by}</a>'


def valid_reply(parent, user, value, mentions):
    """Duplicate reply against replies for topic including topic."""
    ancestors = parent.ancestors.values_list('id', flat=True)
    top_id = min(ancestors) if ancestors else parent.id
    duplicate = Comment.objects.filter(
        (Q(ancestors=top_id) | Q(id=top_id)) & Q(content__iexact=value)
    ).first()
    if duplicate:
        return f'Replied by <a href="/{duplicate.created_by}/{duplicate.base}">@{duplicate.created_by}</a> in thread'
    elif parent.created_by_id == user.id:
        return "Can't reply to yourself"
    elif len(mentions) == 1 and mentions[0].lower() == parent.created_by.username:
        return "Can't mention the author"


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


def valid_username(value, remote_addr='', user_agent='', user_id=0):
    limits = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    ua = parse(user_agent)
    is_browser = ua.is_pc or ua.is_tablet or ua.is_mobile
    if not value:
        return "Username can't be blank"
    elif len(value) > 15:
        return "Username can't be longer than 15 characters"
    elif not all(c in limits for c in value):
        return "Username can be only alphanumeric"
    elif any(slur in value for slur in SLURS):
        return "Username is prohibited"
    elif has_repetions(value):
        return "Username contains repeating characters"
    elif "__" in value:
        return "Username contains consecutive underscores"
    elif value in INVALID:
        return "Username isn't valid"
    elif User.objects.filter(username=value).exclude(id=user_id).exists():
        return "Username is already taken"
    elif remote_addr and User.objects.filter(remote_addr=remote_addr).exists():
        return "Username registered from this IP address"
    elif user_agent and not is_browser:
        return "You aren't using a PC, tablet or mobile phone"


def valid_handle(value):
    limits = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    if len(value) > 15:
        return "Handle can't be longer than 15 characters"
    elif not all(c in limits for c in value):
        return "Handle can be only alphanumeric"


def valid_first_name(value):
    if not value:
        return "First name can't be blank"
    elif len(value) > 15:
        return "First name can't be longer than 15 characters"
    elif len(value) == 1:
        return "First name is just too short"
    elif any(slur in value.lower() for slur in SLURS):
        return "First name is prohibited"
    elif not all(c in LATIN for c in value):
        return "First name should use Latin characters"
    elif has_repetions(value):
        return "First name contains repeating characters"
    elif value.count('-') > 1 or value.startswith('-') or value.endswith('-'):
        return "Only one double-name is allowed"


def valid_last_name(value):
    if len(value) > 15:
        return "Last name can't be longer than 15 characters"
    elif any(slur in value.lower() for slur in SLURS):
        return "Last name is prohibited"
    elif not all(c in LATIN for c in value):
        return "Last name should use Latin characters"
    elif value and has_repetions(value):
        return "Last name contains repeating characters"
    elif value.count('-') > 1 or value.startswith('-') or value.endswith('-'):
        return "Only one double-name is allowed"


def valid_full_name(first_name, last_name):
    if first_name and last_name:
        if first_name.lower() == last_name.lower():
            return "First and last names should be different"
        elif any(slur in f"{first_name}{last_name}".lower() for slur in SLURS):
            return "Full name is prohibited"


def valid_email(value, user_id=0):
    if not value:
        return "Email can't be blank"
    elif len(value) > 120:
        return "Email can't be longer than 120 characters"
    elif len(value) != len(value.encode()):
        return "Email should use English alphabet"
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


def valid_bio(value, username, user_id=0):
    if value:
        mentions, links, hashtags = parse_metadata(value)
        duplicate = User.objects.filter(bio=value).exclude(id=user_id).first()
        if len(value) > 120:
            return "Bio can't be longer than 120 characters"
        elif len(value) != len(value.encode()):
            return "Only English alphabet allowed"
        elif any(slur in value.lower() for slur in SLURS):
            return "Bio contains prohibited words"
        elif duplicate:
            return f'Bio is used by <a href="/{duplicate}">@{duplicate}</a>'
        elif has_repetions(value):
            return "Bio contains repeating characters"
        elif len(mentions) > 1:
            return "Mention a single user"
        elif len(links) > 1:
            return "Link a single address"
        elif len(hashtags) > 1:
            return "Hashtag a single channel"
        elif hashtags and len(hashtags[0]) > 120:
            return "Hashtag can't be longer than 15 characters"
        elif mentions:
            mention = mentions[0].lower()
            if mention == username:
                return "Can't mention yourself"
            elif not User.objects.filter(username=mention).exists():
                return "@{0} isn't an user".format(mention)


def valid_website(value, user_id=0):
    if value:
        duplicate = User.objects.filter(website=value).exclude(id=user_id).first()
        if len(value) > 120:
            return "Website can't be longer than 120 characters"
        elif len(value) != len(value.encode()):
            return "Website should use English alphabet"
        elif not value.startswith(('http://', 'https://')):
            return "Website hasn't a valid http(s) address"
        elif duplicate:
            return f'Website is used by <a href="/{duplicate}">@{duplicate}</a>'
        else:
            try:
                headers = requests.head(
                    value, allow_redirects=True, timeout=5
                ).headers
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
            if country not in WORLD:
                return "Country is invalid"
            elif city not in WORLD[country]:
                return "City is invalid"
        elif value not in WORLD:
            return "Country is invalid"


def valid_emoji(value, user_id=0):
    if value:
        duplicate = User.objects.filter(emoji=value).exclude(id=user_id).first()
        emojis = list(grapheme.graphemes(value))
        if any(emo not in emoji.UNICODE_EMOJI_ENGLISH for emo in emojis):
            return "Emojis only are allowed"
        if len(emojis) > 2:
            return "Emojis are more than two"
        elif len(emojis) == 2 and emojis[0] == emojis[1]:
            return "Emojis are identical"
        elif duplicate:
            return f'Emoji status of <a href="/{duplicate}">@{duplicate}</a>'


def changing(user, current, password1, password2):
    errors = {}
    if not verify_hash(current, user.password):
        errors['current'] = "Password doesn't match"
    errors['password'] = valid_password(password1, password2)
    return {k: v for k, v in errors.items() if v}


def profiling(f, user_id):
    errors = {}
    errors['username'] = valid_username(f['username'], user_id=user_id)
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = valid_full_name(f['first_name'], f['last_name'])
    errors['email'] = valid_email(f['email'], user_id=user_id)
    errors['website'] = valid_website(f['website'], user_id=user_id)
    errors['bio'] = valid_bio(f['bio'], f['username'], user_id=user_id)
    errors['birthday'] = valid_birthday(f['birthday'])
    errors['location'] = valid_location(f['location'])
    errors['emoji'] = valid_emoji(f['emoji'], user_id=user_id)
    return {k: v for k, v in errors.items() if v}


def registration(f):
    errors = {}
    errors['username'] = valid_username(
        f['username'], remote_addr=f['remote_addr'], user_agent=f['user_agent']
    )
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = valid_full_name(f['first_name'], f['last_name'])
    errors['password'] = valid_password(f['password1'], f['password2'])
    errors['email'] = valid_email(f['email'])
    errors['website'] = valid_website(f['website'])
    errors['bio'] = valid_bio(f['bio'], f['username'])
    errors['birthday'] = valid_birthday(f['birthday'])
    errors['location'] = valid_location(f['location'])
    errors['emoji'] = valid_emoji(f['emoji'])
    return {k: v for k, v in errors.items() if v}
