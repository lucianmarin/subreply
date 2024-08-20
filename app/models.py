from os import environ

from django import setup
from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

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
    is_approved = models.BooleanField(default=False)

    emoji = models.CharField(max_length=80, default='')
    birthday = models.CharField(max_length=10, default='')
    location = models.CharField(max_length=60, default='')
    description = models.CharField(max_length=120, default='')
    website = models.CharField(max_length=120, default='')

    phone = models.JSONField(default=dict)
    wallet = models.JSONField(default=dict)
    social = models.JSONField(default=dict)

    class Meta:
        unique_together = ['emoji', 'first_name', 'last_name']

    def __str__(self):
        return self.username

    @cached_property
    def full_name(self):
        if len(self.last_name) == 1:
            self.last_name += "."
        return f"{self.emoji} {self.first_name} {self.last_name}".strip()

    @cached_property
    def short_name(self):
        if len(self.last_name) == 1:
            self.last_name += "."
        return f"{self.first_name} {self.last_name}".strip()

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
    def notif_arrivals(self):
        if self.id == 1:
            return User.objects.filter(is_approved=False).count()
        return 0

    @cached_property
    def follows(self):
        return self.following.values_list('to_user_id', flat=True)

    @cached_property
    def saves(self):
        return self.saved.values_list('post_id', flat=True)

    @cached_property
    def links(self):
        if self.phone:
            self.social['phone'] = self.phone['code'] + self.phone['number']
        return self.social


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
    content = models.CharField(max_length=640, db_index=True)
    link = models.CharField(max_length=240, default='', db_index=True)
    hashtag = models.CharField(max_length=15, default='', db_index=True)
    mention_seen_at = models.FloatField(default=.0, db_index=True)
    reply_seen_at = models.FloatField(default=.0, db_index=True)

    class Meta:
        unique_together = ['parent', 'created_by']

    def __str__(self):
        return self.content

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
    post = models.ForeignKey('Post', on_delete=models.CASCADE,
                             related_name='saved_by')


class Bond(models.Model):
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='following')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE,
                                related_name='followers')
    seen_at = models.FloatField(default=.0, db_index=True)
