# Generated by Django 5.2.1 on 2025-07-17 16:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0050_rename_text_chat_remove_post_hashtag"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="hashtag",
            field=models.CharField(db_index=True, default="", max_length=15),
        ),
    ]
