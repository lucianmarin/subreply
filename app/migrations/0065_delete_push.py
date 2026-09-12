# Generated on 2026-09-12 - remove push notifications

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0064_alter_save_unique_together"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Push",
        ),
    ]
