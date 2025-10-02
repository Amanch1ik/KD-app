"""Auto-merge migration created to resolve conflicting leaf nodes.

This merge records both 0002_alter_userprofile_phone_number and
0019_alter_category_options_alter_order_options_and_more as parents.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0002_alter_userprofile_phone_number'),
        ('delivery', '0019_alter_category_options_alter_order_options_and_more'),
    ]

    operations = [
        migrations.RunPython(lambda apps, schema_editor: None, reverse_code=lambda apps, schema_editor: None),
    ]


