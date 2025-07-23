from falcon.hooks import before
from falcon.constants import MEDIA_JSON
from django.db.models import Count, F, Prefetch, Q, Max

from app.hooks import auth_required, auth_user
from app.models import Bond, Chat, Post, Save, User, Work
from app.serializers import build_entry, build_user
from app.validation import authentication
from project.settings import FERNET

Posts = Post.objects.annotate(
    replies=Count('descendants')
).select_related('created_by')

PPFR = Prefetch('parent', Posts)
PFR = Prefetch('kids', Posts.order_by('-id'))
RPFR = Prefetch('kids', Posts.prefetch_related(PFR))

def paginate(req, qs, limit=16):
    p = req.params.get('p', '1').strip()
    number = int(p) if p.isdecimal() and int(p) else 0
    index = (number - 1) * limit
    return qs[index:index + limit], number


class LoginEndpoint:
    def on_post(self, req, resp):
        resp.content_type = MEDIA_JSON
        form = req.get_media()
        username = form.get('username', '')
        password = form.get('password', '')
        errors, user = authentication(username, password)
        if errors:
            resp.media = errors
        else:
            token = FERNET.encrypt(str(user.id).encode()).decode()
            resp.media = {"token": token}


class FeedEndpoint:
    def fetch_entries(self, user):
        friends = Bond.objects.filter(created_by=user).values('to_user_id')
        entries = Posts.filter(created_by__in=friends).order_by('-id')
        return entries.prefetch_related(PFR, PPFR)

    @before(auth_user)
    @before(auth_required)
    def on_get(self, req, resp):
        resp.content_type = MEDIA_JSON
        entries, page = paginate(req, self.fetch_entries(req.user))
        resp.media = {
            "page": page,
            "entries": [build_entry(entry, parent=True) for entry in entries]
        }
