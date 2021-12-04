from datetime import datetime, timezone
from os import environ

from django import setup
from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from app.const import SOCIAL
from app.helpers import utc_timestamp

if not settings.configured:
    environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    setup()

if settings.DEBUG:
    import logging
    log = logging.getLogger('django.db.backends')
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler())


class User(models.Model):
    username = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=15, default='')
    email = models.CharField(max_length=120, unique=True)
    password = models.CharField(max_length=80)

    joined_at = models.FloatField(default=.0)
    seen_at = models.FloatField(default=.0, db_index=True)
    is_approved = models.BooleanField(default=False)

    emoji = models.CharField(max_length=15, default='')
    birthday = models.CharField(max_length=10, default='')
    location = models.CharField(max_length=60, default='')
    description = models.CharField(max_length=120, default='')
    website = models.CharField(max_length=120, default='')
    links = models.JSONField(default=dict)

    class Meta:
        unique_together = ['emoji', 'first_name', 'last_name']

    def __str__(self):
        return self.username

    @cached_property
    def full_name(self):
        if len(self.last_name) == 1:
            self.last_name += "."
        return "{0} {1} {2}".format(
            self.emoji, self.first_name, self.last_name
        ).strip()

    @cached_property
    def short_name(self):
        if self.emoji:
            return self.emoji
        elif self.last_name:
            return (self.first_name[:1] + self.last_name[:1]).lower()
        return self.first_name[:1].lower()

    @cached_property
    def status(self):
        now = utc_timestamp()
        away = now - 7 * 24 * 3600
        gone = now - 28 * 24 * 3600
        if self.seen_at > away:
            return "here"
        elif gone <= self.seen_at <= away:
            return "away"
        else:
            return "gone"

    @cached_property
    def social(self):
        also = "Also on {0}."
        keys = sorted(self.links)
        holder = ""
        for key in keys[:-2]:
            holder += SOCIAL[key].format(self.links[key]) + ", "
        for index, key in enumerate(keys[-2:]):
            holder += SOCIAL[key].format(self.links[key])
            if not index and len(keys) > 1:
                holder += " and "
        return also.format(holder)

    @cached_property
    def notif_followers(self):
        return self.followers.filter(seen_at=.0).count()

    @cached_property
    def notif_mentions(self):
        return self.mentions.filter(mention_seen_at=.0).count()

    @cached_property
    def notif_replies(self):
        return self.replies.filter(reply_seen_at=.0).count()

    @cached_property
    def lobbies(self):
        if self.id == 1:
            return User.objects.filter(is_approved=False).count()
        return 0

    @cached_property
    def follows(self):
        return self.following.values_list('to_user_id', flat=True)

    @cached_property
    def saves(self):
        return self.saved.values_list('to_comment_id', flat=True)

    def up_seen(self):
        fmt = "%Y-%m-%d-%H"
        last_day = datetime.now(timezone.utc).strftime(fmt)
        last_seen = datetime.fromtimestamp(self.seen_at).strftime(fmt)
        if last_day != last_seen:
            self.seen_at = utc_timestamp()
            self.save(update_fields=['seen_at'])


class Comment(models.Model):
    ancestors = models.ManyToManyField('self', related_name='descendants',
                                       symmetrical=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True,
                               related_name='kids')
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='comments')
    at_user = models.ForeignKey('User', on_delete=models.SET_NULL,
                                null=True, related_name='mentions')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE, null=True,
                                related_name='replies')
    content = models.CharField(max_length=640, db_index=True)
    hashtag = models.CharField(max_length=15, default='')
    link = models.CharField(max_length=120, default='')
    edited_at = models.FloatField(default=.0)
    mention_seen_at = models.FloatField(default=.0, db_index=True)
    reply_seen_at = models.FloatField(default=.0, db_index=True)

    class Meta:
        unique_together = ['parent', 'created_by']

    def __str__(self):
        return self.content

    @cached_property
    def replied(self):
        if not self.replies:
            return 'reply'
        elif self.replies == 1:
            return '1 reply'
        else:
            return '{0} replies'.format(self.replies)

    @cached_property
    def base(self):
        number = self.id
        alphabet, base36 = "0123456789abcdefghijklmnopqrstuvwxyz", ""
        while number:
            number, i = divmod(number, 36)
            base36 = alphabet[i] + base36
        return base36 or alphabet[0]

    def get_ancestors(self):
        if not self.parent:
            return []
        return [self.parent] + self.parent.get_ancestors()

    def set_ancestors(self):
        self.ancestors.set(self.get_ancestors())


class Save(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='saved')
    to_comment = models.ForeignKey('Comment', on_delete=models.CASCADE,
                                   related_name='saved_by')


class Relation(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='following')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE,
                                related_name='followers')
    seen_at = models.FloatField(default=.0, db_index=True)
