from django.core.management.base import BaseCommand
from django.db.models import F

from app.models import Comment, Relation, Save, User


class Command(BaseCommand):
    help = "Count users, comments, etc."

    def handle(self, *args, **options):
        users = User.objects.count()
        subs = Relation.objects.exclude(created_by_id=F('to_user_id')).count()
        saves = Save.objects.count()
        statuses = Comment.objects.filter(parent=None, replies=0).count()
        threads = Comment.objects.filter(parent=None).exclude(replies=0).count()
        replies = Comment.objects.exclude(parent=None).count()
        print('users', users)
        print('subs', subs)
        print('saves', saves)
        print('statuses', statuses)
        print('threads', threads)
        print('replies', replies)
