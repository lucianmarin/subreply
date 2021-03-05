from datetime import datetime, timezone
from os import environ

from django import setup
from django.conf import settings
from django.contrib.postgres import fields
from django.db import models
from django.db.models import F
from django.utils.functional import cached_property


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

    readonly = models.BooleanField(default=False, db_index=True)
    remote_addr = models.GenericIPAddressField()
    joined_at = models.FloatField(default=.0)
    seen_at = models.FloatField(default=.0, db_index=True)

    emoji = models.CharField(max_length=15, default='')
    location = models.CharField(max_length=60, default='')
    birthday = models.CharField(max_length=10, default='')
    bio = models.CharField(max_length=120, default='')
    website = models.CharField(max_length=120, default='')

    # notif_followers = models.PositiveIntegerField(default=0)
    # notif_mentions = models.PositiveIntegerField(default=0)
    # notif_replies = models.PositiveIntegerField(default=0)
    # saves = fields.ArrayField(models.PositiveIntegerField(), default=list)

    def __str__(self):
        return self.username

    @cached_property
    def full_name(self):
        if len(self.last_name) == 1:
            return "{0} {1}.".format(self.first_name, self.last_name)
        return "{0} {1}".format(self.first_name, self.last_name).strip()

    @cached_property
    def short_name(self):
        if self.last_name:
            return "{0} {1}.".format(self.first_name, self.last_name[0])
        return self.first_name

    @cached_property
    def status(self):
        now = datetime.now(timezone.utc).timestamp()
        away = now - 7 * 24 * 3600
        gone = now - 28 * 24 * 3600
        if self.seen_at > away:
            return "here"
        elif gone <= self.seen_at <= away:
            return "away"
        else:
            return "gone"

    # def up_followers(self):
    #     self.notif_followers = self.followers.filter(seen_at=.0).count()
    #     self.save(update_fields=['notif_followers'])

    # def up_mentions(self):
    #     self.notif_mentions = self.mentions.filter(mention_seen_at=.0).count()
    #     self.save(update_fields=['notif_mentions'])

    # def up_replies(self):
    #     self.notif_replies = Comment.objects.filter(
    #         parent__created_by=self, reply_seen_at=.0
    #     ).count()
    #     self.save(update_fields=['notif_replies'])

    # def up_saves(self):
    #     self.saves = list(self.saved.values_list('to_comment_id', flat=True))
    #     self.save(update_fields=['saves'])

    @cached_property
    def notif_followers(self):
        return self.followers.filter(seen_at=.0).count()

    @cached_property
    def notif_mentions(self):
        return self.mentions.filter(mention_seen_at=.0).count()

    @cached_property
    def notif_replies(self):
        return Comment.objects.filter(
            parent__created_by=self, reply_seen_at=.0
        ).count()

    @cached_property
    def saves(self):
        return self.saved.values_list('to_comment_id', flat=True)

    def up_seen(self, remote_addr):
        fmt = "%Y-%m-%d-%p"
        last_day = datetime.now(timezone.utc).strftime(fmt)
        last_seen = datetime.fromtimestamp(self.seen_at).strftime(fmt)
        if last_day != last_seen:
            self.remote_addr = remote_addr
            self.seen_at = datetime.now(timezone.utc).timestamp()
            self.save(update_fields=['remote_addr', 'seen_at'])


class Comment(models.Model):
    ancestors = fields.ArrayField(models.PositiveIntegerField(), default=list)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True,
                               related_name='kids')
    created_at = models.FloatField(default=.0)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,
                                   related_name='comments')
    mentioned = models.ForeignKey('User', on_delete=models.SET_NULL,
                                  null=True, related_name='mentions')
    content = models.CharField(max_length=480, db_index=True)
    hashtag = models.CharField(max_length=15, default='')
    link = models.CharField(max_length=120, default='')
    mention = models.CharField(max_length=15, default='')
    edited_at = models.FloatField(default=.0)
    mention_seen_at = models.FloatField(default=.0)
    reply_seen_at = models.FloatField(default=.0)
    # replies = models.IntegerField(default=0, db_index=True)
    # saves = models.IntegerField(default=0)

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
        if self.parent_id is None:
            return []
        return [self.parent_id] + self.parent.get_ancestors()

    # def add_replies(self):
    #     ancestors = Comment.objects.filter(id__in=self.ancestors)
    #     ancestors.update(replies=F('replies') + 1)

    # def subtract_replies(self):
    #     ancestors = Comment.objects.filter(id__in=self.ancestors)
    #     ancestors.update(replies=F('replies') - 1)

    def up_ancestors(self):
        self.ancestors = self.get_ancestors()
        self.save(update_fields=['ancestors'])

    # @cached_property
    # def replies(self):
    #     return self.kids.count()

    @cached_property
    def saves(self):
        return self.saved_by.count()


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
    seen_at = models.FloatField(default=.0)


class Reset(models.Model):
    created_at = models.FloatField(default=.0)
    email = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=32, default='')
