from json import dumps

from emoji import emojize
from pywebpush import webpush, WebPushException

from app.models import Push
from project.settings import VAPID_PRIVATE_KEY

VAPID_CLAIMS = {"sub": "mailto:push@subreply.com"}


def send_push_to_user(user, title, body, url, tag=None):
    subs = Push.objects.filter(user=user)
    if not subs:
        return

    payload = dumps({
        "title": title,
        "body": body,
        "url": url,
        "tag": tag or "default",
    })

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    }
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as ex:
            if ex.response and ex.response.status_code == 410:
                sub.delete()
