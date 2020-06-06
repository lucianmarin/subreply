from datetime import datetime, timezone
from os import environ

from django import setup
from django.conf import settings
from django.contrib.postgres import fields
from django.db import models
from django.db.models import F

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

    remote_addr = models.GenericIPAddressField()
    joined_at = models.FloatField(default=.0)
    seen_at = models.FloatField(default=.0)
    verified_at = models.FloatField(default=.0)

    emoji = models.CharField(max_length=15, default='')
    country = models.CharField(max_length=2, default='WW')
    birthyear = models.CharField(max_length=4, default='')
    bio = models.CharField(max_length=120, unique=True)
    website = models.CharField(max_length=120, unique=True)

    donations = models.IntegerField(default=0)

    notif_followers = models.PositiveIntegerField(default=0)
    notif_mentions = models.PositiveIntegerField(default=0)
    notif_replies = models.PositiveIntegerField(default=0)
    saved_list = fields.ArrayField(models.PositiveIntegerField(), default=list)

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name).strip()

    @property
    def short_name(self):
        if self.last_name:
            return "{0} {1}.".format(self.first_name, self.last_name[0])
        return self.first_name

    @property
    def status(self):
        now = datetime.now(timezone.utc).timestamp()
        away = now - 7 * 24 * 3600
        gone = now - 28 * 24 * 3600
        if self.seen_at > away:
            return "available"
        elif gone <= self.seen_at <= away:
            return "away"
        else:
            return "unavailable"

    def up_followers(self):
        self.notif_followers = self.followers.filter(seen_at=.0).count()
        self.save(update_fields=['notif_followers'])

    def up_mentions(self):
        self.notif_mentions = self.mentions.filter(seen_at=.0).count()
        self.save(update_fields=['notif_mentions'])

    def up_replies(self):
        self.ex_replies = self.comments.filter(seen_at=.0).count()
        self.save(update_fields=['notif_replies'])

    def up_saves(self):
        self.saved_list = list(self.saves.values_list('to_comment_id', flat=True))
        self.save(update_fields=['saved_list'])

    def up_seen(self, remote_addr):
        fmt = "%Y-%m-%d-%p"
        today = datetime.utcnow().strftime(fmt)
        last_seen = datetime.fromtimestamp(self.seen_at).strftime(fmt)
        if today != last_seen:
            self.remote_addr = remote_addr
            self.seen_at = datetime.utcnow().timestamp()
            self.save(update_fields=['remote_addr', 'seen_at'])

    def __str__(self):
        return self.username


class Comment(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True,
                               related_name='kids')
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='comments')
    mentioned = models.ForeignKey('User', on_delete=models.SET_NULL,
                                  null=True, related_name='mentions')
    content = models.CharField(max_length=480, unique=True)
    hashtag = models.CharField(max_length=15, default='', db_index=True)
    link = models.CharField(max_length=120, default='', db_index=True)
    mention = models.CharField(max_length=15, default='', db_index=True)
    edited_at = models.FloatField(default=.0)
    mention_seen_at = models.FloatField(default=.0)
    reply_seen_at = models.FloatField(default=.0)
    replies = models.IntegerField(default=0, db_index=True)

    @property
    def replied(self):
        if not self.replies:
            return 'reply'
        elif self.replies == 1:
            return '1 reply'
        else:
            return '{0} replies'.format(self.replies)

    def get_ancestors(self):
        if self.parent_id is None:
            return []
        return [self.parent_id] + self.parent.get_ancestors()

    def add_replies(self):
        ancestors = self.get_ancestors()
        comments = Comment.objects.filter(id__in=ancestors)
        comments.update(replied=F('replied') + 1)

    def subtract_replies(self):
        ancestors = self.get_ancestors()
        comments = Comment.objects.filter(id__in=ancestors)
        comments.update(replied=F('replied') - 1)


class Save(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='saves')
    to_comment = models.ForeignKey('Comment', on_delete=models.CASCADE,
                                   related_name='saved')


class Relation(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='following')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE,
                                related_name='followers')
    seen_at = models.FloatField(default=.0)
