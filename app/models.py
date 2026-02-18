from os import environ
from datetime import datetime, timezone

from django import setup
from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from app.utils import utc_timestamp

if not settings.configured:
    environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    setup()

if settings.DEBUG:
    import logging
    logger = logging.getLogger('django.db.backends')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


class User(models.Model):
    username = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=15, default='')
    email = models.CharField(max_length=120, unique=True)
    password = models.CharField(max_length=80)

    created_at = models.FloatField(default=.0)
    seen_at = models.FloatField(default=.0, db_index=True)
    donated = models.FloatField(default=.0)

    emoji = models.CharField(max_length=80, default='')
    birthday = models.CharField(max_length=10, default='')
    location = models.CharField(max_length=60, default='')
    link = models.CharField(max_length=240, default='')
    description = models.CharField(max_length=640, default='')

    phone = models.JSONField(default=dict)
    social = models.JSONField(default=dict)

    class Meta:
        unique_together = ['emoji', 'first_name', 'last_name']

    def __str__(self):
        return self.username

    @cached_property
    def avatar(self):
        if not self.emoji:
            return ":bust_in_silhouette:"
        return self.emoji

    @cached_property
    def full_name(self):
        last_name = self.last_name
        if len(last_name) == 1:
            last_name += "."
        if self.emoji:
            return f"{self.emoji} {self.first_name} {last_name}".strip()
        return f"{self.first_name} {last_name}".strip()

    @cached_property
    def short_name(self):
        last_name = self.last_name
        if len(last_name) == 1:
            last_name += "."
        return f"{self.first_name} {last_name}".strip()

    @cached_property
    def abbr_name(self):
        if self.last_name:
            return self.first_name[:1] + self.last_name[:1]
        return self.first_name[:3]

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
    def notif_messages(self):
        return self.received.filter(seen_at=.0).count()

    @cached_property
    def follows(self):
        return self.following.values_list('to_user_id', flat=True)

    @cached_property
    def saves(self):
        return self.saved.values_list('post_id', flat=True)

    @cached_property
    def links(self):
        social = self.social.copy()
        if self.phone:
            social['telephone'] = self.phone['code'] + self.phone['number']
        return social

    def set_seen(self):
        fmt = "%Y-%m-%d-%H-%M"
        last_day = datetime.now(timezone.utc).strftime(fmt)
        last_seen = datetime.fromtimestamp(self.seen_at).strftime(fmt)
        if last_day != last_seen:
            self.seen_at = utc_timestamp()
            self.save(update_fields=['seen_at'])


class Post(models.Model):
    ancestors = models.ManyToManyField('self', related_name='descendants',
                                       symmetrical=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True,
                               related_name='kids')
    created_at = models.FloatField(default=.0)
    edited_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='posts')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE, null=True,
                                related_name='replies')
    at_user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True,
                                related_name='mentions')
    title = models.CharField(max_length=240, default='', db_index=True)
    content = models.CharField(max_length=640, db_index=True)
    body = models.TextField(default='')
    link = models.CharField(max_length=240, default='', db_index=True)
    hashtag = models.CharField(max_length=15, default='', db_index=True)
    mention_seen_at = models.FloatField(default=.0, db_index=True)
    reply_seen_at = models.FloatField(default=.0, db_index=True)

    class Meta:
        unique_together = ['parent', 'created_by']

    def __str__(self):
        return self.content

    def set_ancestors(self):
        if self.parent:
            self.ancestors.set(list(self.parent.ancestors.all()) + [self.parent])
        else:
            self.ancestors.clear()


class Save(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='saved')
    post = models.ForeignKey('Post', on_delete=models.CASCADE,
                             related_name='saved_by')


class Bond(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='following')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE,
                                related_name='followers')
    seen_at = models.FloatField(default=.0, db_index=True)


class Chat(models.Model):
    content = models.CharField(max_length=640)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='sent')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='received')
    created_at = models.FloatField(default=.0)
    seen_at = models.FloatField(default=.0)
