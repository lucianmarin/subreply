from django.core.management.base import BaseCommand

from app.models import Comment, Relation, Save, User


class Command(BaseCommand):
    help = "Count users, comments, etc."

    def handle(self, *args, **options):
        users = User.objects.count()
        relations = Relation.objects.count()
        saves = Save.objects.count()
        threads = Comment.objects.filter(parent=None).count()
        replies = Comment.objects.exclude(parent=None).count()
        print('users', users)
        print('relations', relations)
        print('saves', saves)
        print('threads', threads)
        print('replies', replies)
