import emails
from emails.template import JinjaTemplate as T
from project.settings import SMTP


m = emails.Message(
    html=T("<html><p>Hello, You can reset your password on Subreply for @{{ username }} using this link https://subreply.com/reset/{{ reset_hash }} then you're logged in with the new credentials."),
    text=T("Hello, You can reset your password on Subreply for @{{ username }} using this link https://subreply.com/reset/{{ reset_hash }} then you're logged in with the new credentials."),
    subject=T("Reset password on Subreply"),
    mail_from=("Subreply", "subreply@outlook.com")
)

response = m.send(
    render={"username": "@username", "reset_hash": "hexhex"},
    to='marin.lucian@gmail.com',
    smtp=SMTP
)

if response.status_code == 250:
    print("message sent")
else:
    print("message not sent")
