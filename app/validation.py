import emoji
import grapheme
import requests
from django.db.models import Q
from dns.resolver import query as dns_query

from app.filters import shortdate
from app.const import COUNTRIES, LATIN, MAX_YEAR, MIN_YEAR
from app.helpers import has_repetions, parse_metadata, verify_hash
from app.models import Comment, User
from project.settings import INVALID, SLURS


def valid_content(value, user):
    mentions, links, hashtags = parse_metadata(value)
    # duplicate topic against old topics
    # duplicate reply against replies for topic including topic
    # duplicate content against all account content
    duplicate = Comment.objects.filter(
        content__iexact=value, created_by=user
    ).first()
    if not value:
        return "Status can't be blank"
    elif len(value) > 480:
        return "Status can't be longer than 480 characters"
    elif len(value) != len(value.encode()):
        return "Only English alphabet allowed"
    elif duplicate:
        return f'You wrote this <a href="/{duplicate.created_by}/{duplicate.base}">{shortdate(duplicate.created_at)} ago</a>'
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
    duplicate = Comment.objects.filter(
        content__iexact=value, parent=None
    ).first()
    if duplicate:
        return f'Thread started by <a href="/{duplicate.created_by}/{duplicate.base}">@{duplicate.created_by}</a>'


def valid_reply(entry, user, value, mentions):
    t_id = min(entry.ancestors) if entry.ancestors else entry.id
    duplicate = Comment.objects.filter(
        (Q(ancestors__contains=[t_id]) | Q(id=t_id)) & Q(content__iexact=value)
    ).first()
    if duplicate:
        return f'Replied by <a href="/{duplicate.created_by}/{duplicate.base}">@{duplicate.created_by}</a> in thread'
    elif entry.created_by_id == user.id:
        return "Can't reply to yourself"
    elif len(mentions) == 1 and mentions[0].lower() == entry.created_by.username:
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


def valid_username(value, remote_addr='', user_id=0):
    limits = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
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
    elif value in INVALID:
        return "Username isn't valid"
    elif "__" in value:
        return "Username has consecutive underscores"
    elif remote_addr and User.objects.filter(remote_addr=remote_addr).exists():
        return "Username registered from this IP address"
    elif User.objects.filter(username=value).exclude(id=user_id).exists():
        return "Username is already taken"


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


def valid_last_name(value):
    if len(value) > 15:
        return "Last name can't be longer than 15 characters"
    elif any(slur in value.lower() for slur in SLURS):
        return "Last name is prohibited"
    elif not all(c in LATIN for c in value):
        return "Last name should use Latin characters"
    elif value and has_repetions(value):
        return "Last name contains repeating characters"


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
    else:
        handle, domain = value.split('@', 1)
        try:
            has_mx = bool(dns_query(domain, 'MX'))
        except Exception as e:
            has_mx = False
            print(e)
        if not has_mx:
            return "Email can't be sent to this address"
        elif User.objects.filter(email=value).exclude(id=user_id).exists():
            return "Email is used by someone else"


def valid_bio(value, username, user_id=0):
    if value:
        mentions, links, hashtags = parse_metadata(value)
        duplicate = User.objects.filter(bio=value).exclude(id=user_id).exists()
        if len(value) > 120:
            return "Bio can't be longer than 120 characters"
        elif len(value) != len(value.encode()):
            return "Only English alphabet allowed"
        elif any(slur in value.lower() for slur in SLURS):
            return "Bio contains prohibited words"
        elif duplicate:
            return "Bio is used by someone else"
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
        duplicate = User.objects.filter(website=value).exclude(id=user_id).exists()
        if len(value) > 120:
            return "Website can't be longer than 120 characters"
        elif len(value) != len(value.encode()):
            return "Website should use English alphabet"
        elif not value.startswith(('http://', 'https://')):
            return "Website hasn't a valid http(s) address"
        elif duplicate:
            return "Website is used by someone else"
        else:
            try:
                headers = requests.head(value, allow_redirects=True, timeout=5).headers
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
    elif len(value1) != sum([len(p) for p in value1.split()]):
        return "Password contains spaces"
    elif value1 == value1.lower():
        return "Password needs an uppercase letter"
    elif value1 == value1.upper():
        return "Password needs a lowercase letter"


def valid_birthyear(value):
    if value:
        if len(value) != 4:
            return "Birthday as 4-digit year"
        elif value not in map(str, range(MIN_YEAR, MAX_YEAR + 1)):
            return "Birthday year from {0} to {1}".format(MIN_YEAR, MAX_YEAR)


def valid_country(value):
    if value not in COUNTRIES:
        return "Country code is invalid"


def valid_emoji(value, user_id=0):
    if value:
        duplicate = User.objects.filter(emoji=value).exclude(id=user_id).exists()
        if grapheme.length(value) != emoji.emoji_count(value):
            return "Emoji only for status"
        elif emoji.emoji_count(value) > 2:
            return "Emoji are too many"
        elif emoji.emoji_count(value) == 2 and value[0] == value[1]:
            return "Emoji should be different"
        elif duplicate:
            return "Emoji already taken"


def changing(user, current, password1, password2):
    errors = {}
    if not verify_hash(current, user.password):
        errors['current'] = "Password doesn't match"
    errors['password'] = valid_password(password1, password2)
    errors = {k: v for k, v in errors.items() if v}
    return errors


def profiling(f, user_id):
    errors = {}
    errors['username'] = valid_username(f['username'], user_id=user_id)
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = valid_full_name(f['first_name'], f['last_name'])
    errors['email'] = valid_email(f['email'], user_id=user_id)
    errors['website'] = valid_website(f['website'], user_id=user_id)
    errors['bio'] = valid_bio(f['bio'], f['username'], user_id=user_id)
    errors['birthyear'] = valid_birthyear(f['birthyear'])
    errors['country'] = valid_country(f['country'])
    errors['emoji'] = valid_emoji(f['emoji'], user_id=user_id)
    errors = {k: v for k, v in errors.items() if v}
    return errors


def registration(f):
    errors = {}
    errors['username'] = valid_username(
        f['username'], remote_addr=f['remote_addr']
    )
    errors['first_name'] = valid_first_name(f['first_name'])
    errors['last_name'] = valid_last_name(f['last_name'])
    errors['full_name'] = valid_full_name(f['first_name'], f['last_name'])
    errors['password'] = valid_password(f['password1'], f['password2'])
    errors['email'] = valid_email(f['email'])
    errors['website'] = valid_website(f['website'])
    errors['bio'] = valid_bio(f['bio'], f['username'])
    errors['birthyear'] = valid_birthyear(f['birthyear'])
    errors['country'] = valid_country(f['country'])
    errors['emoji'] = valid_emoji(f['emoji'])
    errors = {k: v for k, v in errors.items() if v}
    return errors
