from django.core.management.base import BaseCommand

from app.models import User


class Command(BaseCommand):
    help = "Delete inactive users."

    def get_user(self):
        users = User.objects.filter(comments=None, saved=None).order_by('seen_at')
        return users.first()

    def handle(self, *args, **options):
        user = self.get_user()
        user.delete()
