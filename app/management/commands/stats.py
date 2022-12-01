from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import F

from app.models import Comment, Relation, Save, User


class Command(BaseCommand):
    help = "Count accounts, comments, etc."
    years = range(2014, datetime.now().year + 1)

    def total(self):
        accounts = User.objects.count()
        relations = Relation.objects.exclude(
            created_by_id=F('to_user_id')
        ).count()
        saves = Save.objects.count()
        threads = Comment.objects.filter(parent=None).count()
        replies = Comment.objects.exclude(parent=None).count()
        print('total:')
        print('  accounts:', accounts)
        print('  relations:', relations)
        print('  saves:', saves)
        print('  threads:', threads)
        print('  replies:', replies)

    def yearly(self):
        for year in self.years:
            first_day = datetime(year, 1, 1).timestamp()
            last_day = datetime(year, 12, 31).timestamp()
            accounts = User.objects.filter(
                created_at__gt=first_day, created_at__lt=last_day
            ).count()
            relations = Relation.objects.filter(
                created_at__gt=first_day, created_at__lt=last_day
            ).exclude(created_by_id=F('to_user_id')).count()
            saves = Save.objects.filter(
                created_at__gt=first_day, created_at__lt=last_day
            ).count()
            threads = Comment.objects.filter(
                created_at__gt=first_day, created_at__lt=last_day,
                parent=None
            ).count()
            replies = Comment.objects.filter(
                created_at__gt=first_day, created_at__lt=last_day
            ).exclude(parent=None).count()
            print(f'{year}:')
            print('  accounts:', accounts)
            print('  relations:', relations)
            print('  saves:', saves)
            print('  threads:', threads)
            print('  replies:', replies)

    def handle(self, *args, **options):  # noqa
        self.yearly()
        self.total()
