from cgi import FieldStorage
from datetime import datetime, timezone
from os import remove

from django.db.models import Max, Q
from falcon import status_codes
from falcon.errors import HTTPNotFound
from falcon.hooks import before
from falcon.redirects import HTTPFound
from unidecode import unidecode

from app.const import COUNTRIES
from app.helpers import make_hash, parse_metadata, save_image
from app.hooks import auth_user, login_required
from app.jinja import env
from app.models import Comment, Relation, Save, User
from app.validation import (authentication, changing, discussion, erasing,
                            profiling, registration)
from project.settings import DEBUG, MAX_AGE, F


def qsr(qs, p=0):
    start = int(p) * 15
    end = (int(p) + 1) * 15
    return qs.select_related('created_by')[start:end]


def pagination(req, resp, entries):
    page = req.params.get('p', '').strip()
    if page and page.isdecimal():
        template = env.get_template('pages/page.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries, page),
            counter=entries.count(), next=int(page) + 1
        )
        return True
    return False


class StaticResource(object):
    binary = ['png', 'jpg', 'woff']
    mime_types = {
        'js': "application/javascript",
        'json': "application/json",
        'css': "text/css",
        'woff': "font/woff",
        'png': "image/png",
        'jpg': "image/jpeg"
    }

    def on_get(self, req, resp, filename):
        print("load", filename)
        name, ext = filename.split('.')
        mode = 'rb' if ext in self.binary else 'r'
        resp.status = status_codes.HTTP_200
        resp.content_type = self.mime_types[ext]
        with open(f'static/{filename}', mode) as f:
            resp.body = f.read()


class MainResource:
    @before(auth_user)
    def on_get(self, req, resp):
        if req.user:
            raise HTTPFound('/feed')
        else:
            raise HTTPFound('/search')


class PinResource:
    @before(auth_user)
    def on_get(self, req, resp, id):
        member = User.objects.filter(id=id).first()
        if member:
            raise HTTPFound('/{0}'.format(member))
        if req.user:
            raise HTTPFound('/feed')
        else:
            raise HTTPFound('/search')


class AboutResource:
    @before(auth_user)
    def on_get(self, req, resp):
        template = env.get_template('pages/about.html')
        resp.body = template.render(user=req.user, view='about')


class FeedResource:
    def fetch_entries(self, user):
        friends = Relation.objects.filter(created_by=user).values('to_user_id')
        return Comment.objects.filter(created_by__in=friends).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        status = req.params.get('s', '').strip()
        form = FieldStorage(fp=req.stream, environ=req.env)
        entries = self.fetch_entries(req.user)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), status=status,
            errors={}, form=form, counter=entries.count(),
            view='feed'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        content = unidecode(form.getvalue('content', ''))
        content = " ".join([p.strip() for p in content.split()])
        errors = discussion(content, req.user)
        if errors:
            entries = self.fetch_entries(req.user)
            template = env.get_template('pages/regular.html')
            resp.body = template.render(
                user=req.user, entries=qsr(entries), status='',
                errors=errors, form=form, counter=entries.count(),
                view='feed'
            )
        else:
            mentions, links, hashtags = parse_metadata(content)
            extra = {}
            extra['hashtag'] = hashtags[0].lower() if hashtags else ''
            extra['link'] = links[0].lower() if links else ''
            extra['mention'] = mentions[0].lower() if mentions else ''
            extra['mentioned'] = User.objects.get(username=mentions[0].lower()) if mentions else None
            c, is_new = Comment.objects.get_or_create(
                content=content,
                created_at=datetime.utcnow().timestamp(),
                created_by=req.user,
                **extra
            )
            if c.mentioned:
                c.mentioned.up_mentions()
            raise HTTPFound('/')


class SearchResource:
    def fetch_results(self, terms):
        query = Q(content__icontains=terms[0])
        for term in terms[1:]:
            query &= Q(content__icontains=term)
        return Comment.objects.filter(query).order_by('pinned_by_id', '-id')

    def fetch_entries(self):
        last_ids = User.objects.annotate(last_id=Max('comments__id')).values('last_id')
        return Comment.objects.filter(id__in=last_ids).order_by('-id')

    @before(auth_user)
    def on_get(self, req, resp):
        q = req.params.get('q', '').strip()
        terms = [t for t in q.split()]
        entries = self.fetch_results(terms) if terms else self.fetch_entries()
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), q=q, counter=entries.count(),
            view='search'
        )


class ProfileResource:
    def fetch_threads(self, user):
        return Comment.objects.filter(created_by=user, parent=None).order_by('-id')

    def fetch_replies(self, user):
        return Comment.objects.filter(created_by=user).exclude(parent=None).order_by('-id')

    @before(auth_user)
    def on_get_r(self, req, resp, username):
        self.get_profile(req, resp, username, 'replies')

    @before(auth_user)
    def on_get_t(self, req, resp, username):
        self.get_profile(req, resp, username, 'threads')

    def get_profile(self, req, resp, username, tab):
        form = FieldStorage(fp=req.stream, environ=req.env)
        member = User.objects.filter(username=username).first()
        if not member:
            template = env.get_template('pages/404.html')
            resp.body = template.render(user=req.user, url=username)
            resp.status = status_codes.HTTP_404
            return
        entries = self.fetch_threads(member) if tab == 'threads' else self.fetch_replies(member)
        threads = self.fetch_threads(member).count()
        replies = self.fetch_replies(member).count()
        is_following = Relation.objects.filter(
            created_by=req.user, to_user=member
        ).exists() if req.user else False
        country = COUNTRIES[member.country]
        template = env.get_template('pages/profile.html')
        resp.body = template.render(
            user=req.user, member=member, entries=qsr(entries),
            tab=tab, threads=threads, replies=replies,
            is_following=is_following, country=country,
            counter=entries.count(), form=form, errors={}, status="@lucian ",
            view='profile'
        )


class FollowingResource:
    def fetch_entries(self, user):
        friends = Relation.objects.filter(created_by=user).exclude(to_user=user).values('to_user_id')
        last_ids = User.objects.filter(id__in=friends).annotate(
            last_id=Max('comments__id')
        ).values('last_id')
        return Comment.objects.filter(id__in=last_ids).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        counter = Relation.objects.filter(created_by=req.user).exclude(to_user=req.user).count()
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=counter,
            description='Latest status from people you follow',
            view='following'
        )


class FollowersResource:
    def fetch_entries(self, user):
        friends = Relation.objects.filter(to_user=user).exclude(created_by=user).values('created_by_id')
        last_ids = User.objects.filter(id__in=friends).annotate(
            last_id=Max('comments__id')
        ).values('last_id')
        return Comment.objects.filter(id__in=last_ids).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        counter = Relation.objects.filter(to_user=req.user).exclude(created_by=req.user).count()
        if req.user.notif_followers:
            Relation.objects.filter(
                to_user=req.user, seen_at=.0
            ).update(seen_at=datetime.utcnow().timestamp())
            req.user.notif_followers = 0
            req.user.save(update_fields=['notif_followers'])
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=counter,
            description='Latest status from your followers',
            view='followers'
        )


class LinksResource:
    def fetch_entries(self, user):
        friends = Relation.objects.filter(created_by=user).values('to_user_id')
        return Comment.objects.filter(created_by_id__in=friends).exclude(link='').order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=entries.count(),
            description='Links from people you follow',
            view='links'
        )


class PeopleResource:
    def fetch_entries(self, user):
        users = User.objects.filter(country=user.country).values('id')
        return Comment.objects.filter(created_by__in=users).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=entries.count(),
            title=COUNTRIES[req.user.country],
            description='Statuses from people in your country',
            view='People'
        )


class MentionsResource:
    def fetch_entries(self, user):
        return Comment.objects.filter(mentioned=user).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        if req.user.notif_mentions:
            Comment.objects.filter(
                mentioned=req.user, seen_at=.0
            ).update(seen_at=datetime.utcnow().timestamp())
            req.user.notif_mentions = 0
            req.user.save(update_fields=['notif_mentions'])
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=entries.count(),
            description='People who mentioned you lately',
            view='mentions'
        )


class RepliesResource:
    def fetch_entries(self, user):
        return Comment.objects.exclude(pinned_by=None).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        if req.user.notif_pins:
            Comment.objects.filter(
                created_by=req.user, seen_at=.0
            ).exclude(
                pinned_by=None
            ).update(seen_at=datetime.utcnow().timestamp())
            req.user.notif_pins = 0
            req.user.save(update_fields=['notif_pins'])
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=entries.count(),
            description='Pinned statuses across the network',
            view='pins'
        )


class SavesResource:
    def fetch_entries(self, user):
        saves = Save.objects.filter(created_by=user).values('to_comment_id')
        return Comment.objects.filter(id__in=saves).order_by('-id')

    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        entries = self.fetch_entries(req.user)
        template = env.get_template('pages/regular.html')
        resp.body = template.render(
            user=req.user, entries=qsr(entries), counter=entries.count(),
            description='Statuses you saved lately',
            view='saves'
        )


class FollowResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username).first()
        if not member:
            raise HTTPNotFound()
        if req.user and member.id != req.user.id:
            Relation.objects.get_or_create(
                created_at=datetime.utcnow().timestamp(),
                created_by=req.user,
                to_user=member
            )
            member.up_followers()
        raise HTTPFound(req.referer)


class UnfollowResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp, username):
        member = User.objects.filter(username=username).first()
        if not member:
            raise HTTPNotFound()
        if req.user and member.id != req.user.id:
            Relation.objects.filter(
                created_by=req.user, to_user=member
            ).delete()
            member.up_followers()
        raise HTTPFound(req.referer)


class EraseResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/erase.html')
        resp.body = template.render(
            user=req.user, errors={}, form=form,
            view='erase'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        password = form.getvalue('password', '')
        confirmation = form.getvalue('confirmation', '')
        warning = form.getvalue('warning', '')
        print(confirmation, warning)
        errors = erasing(req.user, password, confirmation, warning)
        if errors:
            template = env.get_template('pages/erase.html')
            resp.body = template.render(
                user=req.user, errors=errors, form=form,
                view='erase'
            )
        else:
            remove("media/u.{0}.jpg".format(req.user.id))
            req.user.delete()
            resp.unset_cookie('identity')
            raise HTTPFound('/search')


class PasswordResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/password.html')
        resp.body = template.render(
            user=req.user, errors={}, form=form,
            view='password'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        current = form.getvalue('current', '')
        password1 = form.getvalue('password1', '')
        password2 = form.getvalue('password2', '')
        errors = changing(req.user, current, password1, password2)
        if errors:
            template = env.get_template('pages/password.html')
            resp.body = template.render(
                user=req.user, errors=errors, form=form,
                view='password'
            )
        else:
            req.user.password = make_hash(password1)
            req.user.save()
            resp.unset_cookie('identity')
            raise HTTPFound('/login')


class SettingsResource:
    @before(auth_user)
    @before(login_required)
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/settings.html')
        resp.body = template.render(
            user=req.user, errors={}, form=form, countries=COUNTRIES,
            view='settings'
        )

    @before(auth_user)
    @before(login_required)
    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        f['username'] = form.getvalue('username', '').strip().lower()
        fn_parts = form.getvalue('first_name', '').split()
        f['first_name'] = " ".join([p.strip() for p in fn_parts])
        ln_parts = form.getvalue('last_name', '').split()
        f['last_name'] = " ".join([p.strip() for p in ln_parts])
        f['email'] = form.getvalue('email', '').strip().lower()
        bio_parts = form.getvalue('bio', '').split()
        f['bio'] = " ".join([p.strip() for p in bio_parts])
        f['emoji'] = form.getvalue('emoji', '').strip()
        f['birthyear'] = form.getvalue('birthyear', '').strip()
        f['country'] = form.getvalue('country', '')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = profiling(f, req.user.id)
        if errors:
            template = env.get_template('pages/settings.html')
            resp.body = template.render(
                user=req.user, errors=errors, form=form, countries=COUNTRIES,
                view='settings'
            )
        else:
            for field, value in f.items():
                if getattr(req.user, field, '') != value:
                    setattr(req.user, field, value)
            req.user.save()
            raise HTTPFound('/{0}'.format(req.user))


class LoginResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/login.html')
        resp.body = template.render(errors={}, form=form, view='login')

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        username = form.getvalue('username', '').strip().lower()
        password = form.getvalue('password', '').strip()
        errors, user = authentication(username, password)
        if errors:
            template = env.get_template('pages/login.html')
            resp.body = template.render(errors=errors, form=form, view='login')
        else:
            token = F.encrypt(str(user.id).encode())
            resp.set_cookie('identity', token.decode(), max_age=MAX_AGE)
            raise HTTPFound('/feed')


class LogoutResource:
    def on_get(self, req, resp):
        resp.unset_cookie('identity')
        raise HTTPFound('/search')


class RegisterResource:
    def on_get(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        template = env.get_template('pages/register.html')
        resp.body = template.render(countries=COUNTRIES, errors={}, form=form, view='register')

    def on_post(self, req, resp):
        form = FieldStorage(fp=req.stream, environ=req.env)
        f = {}
        f['remote_addr'] = '127.0.0.2' if DEBUG else req.access_route[0]
        f['username'] = form.getvalue('username', '').strip().lower()
        fn_parts = form.getvalue('first_name', '').split()
        f['first_name'] = " ".join([p.strip() for p in fn_parts])
        ln_parts = form.getvalue('last_name', '').split()
        f['last_name'] = " ".join([p.strip() for p in ln_parts])
        f['password1'] = form.getvalue('password1', '')
        f['password2'] = form.getvalue('password2', '')
        f['email'] = form.getvalue('email', '').strip().lower()
        bio_parts = form.getvalue('bio', '').split()
        f['bio'] = " ".join([p.strip() for p in bio_parts])
        f['emoji'] = form.getvalue('emoji', '').strip()
        f['birthyear'] = form.getvalue('birthyear', '').strip()
        f['country'] = form.getvalue('country', '')
        f['website'] = form.getvalue('website', '').strip().lower()
        errors = registration(f)
        if errors:
            template = env.get_template('pages/register.html')
            resp.body = template.render(
                countries=COUNTRIES, errors=errors, form=form, view='register'
            )
        else:
            utc_timestamp = datetime.now(timezone.utc).timestamp()
            user, is_new = User.objects.get_or_create(
                username=f['username'],
                defaults={
                    'first_name': f['first_name'],
                    'last_name': f['last_name'],
                    'password': make_hash(f['password1']),
                    'email': f['email'],
                    'website': f['website'],
                    'joined_at': utc_timestamp,
                    'seen_at': utc_timestamp,
                    'remote_addr': f['remote_addr']
                }
            )
            Relation.objects.get_or_create(
                created_at=utc_timestamp,
                seen_at=utc_timestamp,
                created_by=user, to_user=user
            )
            token = F.encrypt(str(user.id).encode()).decode()
            resp.set_cookie('identity', token, max_age=MAX_AGE)
            raise HTTPFound('/')
