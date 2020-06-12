import json

from dateutil.parser import parse
from django.core.management.base import BaseCommand
from unidecode import unidecode

from app.models import Comment, User


class Command(BaseCommand):
    help = "Fetch users, comments from db.json."
    users = {}
    comments = {}

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

    def fetch_comments(self, fields, pk):
        comment, is_new = Comment.objects.get_or_create(
            ancestors=[],
            parent=self.comments.get(fields['parent']),
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            mentioned=None,
            content=unidecode(fields['content'])[:480]
        )
        self.comments[pk] = comment
        comment.up_ancestors()
        comment.add_replies()

    def handle(self, *args, **options):
        with open('db_nodupes.json') as db:
            rows = json.load(db)
            for row in rows:
                if row['model'] == "app.user":
                    self.fetch_users(row['fields'], row['pk'])
                elif row['model'] == "app.comment":
                    self.fetch_comments(row['fields'], row['pk'])
