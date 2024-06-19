import json

from dateutil.parser import parse
from django.core.management.base import BaseCommand
from unidecode import unidecode

from app.forms import get_metadata
from app.models import Bond, Post, Save, User


class Command(BaseCommand):
    help = "Fetch users, posts from db.json."
    users = {}
    posts = {}

    def fetch_users(self, fields, pk):
        user, is_new = User.objects.get_or_create(
            username=fields['username'][:15],
            first_name=unidecode(fields['first_name'])[:15],
            last_name=unidecode(fields['last_name'])[:15],
            email=fields['email'],
            password=fields['password'],
            joined_at=parse(fields['date_joined']).timestamp(),
            seen_at=parse(fields['last_login']).timestamp(),
            country=fields['location'],
            bio=unidecode(fields['bio'])[:120],
            website=unidecode(fields['website'])[:120],
            remote_addr="0.0.0.0"
        )
        self.users[pk] = user

    def fetch_posts(self, fields, pk):
        hashtags, links, mentions = get_metadata(fields['content'])
        at_user = None
        if mentions:
            at_user = User.objects.filter(username=mentions[0].lower()).first()
        post, is_new = Post.objects.get_or_create(
            ancestors=None,
            parent=self.posts.get(fields['parent']),
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            at_user=at_user,
            content=fields['content']
        )
        print(post.id, pk)
        self.posts[pk] = post
        post.set_ancestors()

    def fetch_likes(self, fields):
        Save.objects.get_or_create(
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            post=self.posts.get(fields['post'])
        )

    def fetch_bonds(self, fields):
        Bond.objects.get_or_create(
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            to_user=self.users.get(fields['to_user'])
        )

    def handle(self, *args, **options):
        with open('db_clean.json') as db:
            rows = json.load(db)
            for row in rows:
                if row['model'] == "app.user":
                    self.fetch_users(row['fields'], row['pk'])
                elif row['model'] == "app.post":
                    self.fetch_posts(row['fields'], row['pk'])
                elif row['model'] == "app.postlike":
                    self.fetch_likes(row['fields'])
                elif row['model'] == "app.relationship":
                    self.fetch_bonds(row['fields'])
