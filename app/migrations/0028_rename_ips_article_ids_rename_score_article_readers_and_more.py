# Generated by Django 4.0.4 on 2022-04-29 07:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0027_message'),
    ]

    operations = [
        migrations.RenameField(
            model_name='article',
            old_name='ips',
            new_name='ids',
        ),
        migrations.RenameField(
            model_name='article',
            old_name='score',
            new_name='readers',
        ),
        migrations.AlterField(
            model_name='message',
            name='content',
            field=models.TextField(),
        ),
    ]
