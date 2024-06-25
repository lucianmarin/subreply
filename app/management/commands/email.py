from django.core.management.base import BaseCommand
from emails import Message
from emails.template import JinjaTemplate

from app.models import User
from project.settings import SMTP
from project.vars import ACTIVITY_HTML, ACTIVITY_TEXT


class Command(BaseCommand):
    help = "Email inactive users."

    def get_user(self, mock=True):
        users = User.objects.filter(is_notified=False).order_by('seen_at')
        if mock:
            users = users.filter(id__in=[1])
        for user in users:
            notifs = []
            if user.notif_followers:
                notifs.append('followers')
            if user.notif_mentions:
                notifs.append('mentions')
            if user.notif_replies:
                notifs.append('replies')
            user.notifs = ", ".join(notifs)
            if user.notifs:
                return user

    def send_mail(self, user):
        # compose email
        m = Message(
            html=JinjaTemplate(ACTIVITY_HTML),
            text=JinjaTemplate(ACTIVITY_TEXT),
            subject="Activity left unseen on Subreply",
            mail_from=("Subreply", "subreply@outlook.com")
        )
        # send email
        response = m.send(
            render={"username": user, "notifs": user.notifs},
            to=user.email,
            smtp=SMTP
        )
        # fallback
        if response.status_code == 250:
            print(user, "sent")
            user.is_notified = True
            user.save(update_fields=['is_notified'])
        else:
            print(user, "failed")

    def handle(self, *args, **options):
        to_user = self.get_user(mock=False)
        if to_user:
            self.send_mail(to_user)
