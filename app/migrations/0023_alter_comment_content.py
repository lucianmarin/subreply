# Generated by Django 3.2.8 on 2021-11-17 19:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0022_rename_bio_user_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='content',
            field=models.CharField(db_index=True, max_length=800),
        ),
    ]
