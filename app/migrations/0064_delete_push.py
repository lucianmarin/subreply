# Generated on 2026-09-12 - remove push notifications

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0063_bond_unique_pair"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Push",
        ),
    ]
