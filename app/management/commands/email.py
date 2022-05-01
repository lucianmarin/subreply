from json import dump

from django.core.management.base import BaseCommand
from emails import Message as Email
from emails.template import JinjaTemplate

from app.models import User
from project.settings import SMTP
from project.vars import ACTIVITY_HTML, ACTIVITY_TEXT


class Command(BaseCommand):
    help = "Email inactive users."
    users = []
    mails = []
    fails = []

    def get_users(self, mock=True):
        users = User.objects.order_by('seen_at')
        if mock:
            users = users.filter(id__in=[1, 2])
        for user in users:
            notifs = []
            if user.notif_followers:
                notifs.append('followers')
            if user.notif_mentions:
                notifs.append('mentions')
            if user.notif_messages:
                notifs.append('messages')
            if user.notif_replies:
                notifs.append('replies')
            user.notifs = ", ".join(notifs)
            if user.notifs:
                self.users.append(user)

    def send_mail(self, user):
        # compose email
        m = Email(
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
            self.mails.append(user.username)
        else:
            self.fails.append(user.username)

    def handle(self, *args, **options):
        self.get_users(mock=False)
        for user in self.users:
            print(user, '-', user.notifs)
            self.send_mail(user)
        with open('emails.json', 'w') as outfile:
            data = {'mails': self.mails, 'fails': self.fails}
            dump(data, outfile)
