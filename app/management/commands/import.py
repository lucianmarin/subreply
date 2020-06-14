import json

from dateutil.parser import parse
from django.core.management.base import BaseCommand
from unidecode import unidecode

from app.models import Comment, Relation, Save, User
from app.helpers import parse_metadata


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
        mentions, links, hashtags = parse_metadata(fields['content'])
        mentioned = None
        if mentions:
            mentioned = User.objects.filter(username=mentions[0].lower()).first()
        comment, is_new = Comment.objects.get_or_create(
            ancestors=[],
            parent=self.comments.get(fields['parent']),
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            mentioned=mentioned,
            content=fields['content']
        )
        print(comment.id, pk)
        self.comments[pk] = comment
        comment.up_ancestors()
        comment.add_replies()

    def fetch_likes(self, fields):
        Save.objects.get_or_create(
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            to_comment=self.comments.get(fields['comment'])
        )

    def fetch_relations(self, fields):
        Relation.objects.get_or_create(
            created_at=parse(fields['created_at']).timestamp(),
            created_by=self.users.get(fields['created_by']),
            to_user=self.users.get(fields['to_user'])
        )

    def up_things(self):
        for user in User.objects.order_by('id'):
            user.up_followers()
            user.up_mentions()
            user.up_replies()
            user.up_saves()

    def handle(self, *args, **options):
        with open('db_clean.json') as db:
            rows = json.load(db)
            for row in rows:
                if row['model'] == "app.user":
                    self.fetch_users(row['fields'], row['pk'])
                elif row['model'] == "app.comment":
                    self.fetch_comments(row['fields'], row['pk'])
                elif row['model'] == "app.commentlike":
                    self.fetch_likes(row['fields'])
                elif row['model'] == "app.relationship":
                    self.fetch_relations(row['fields'])
            self.up_things()
