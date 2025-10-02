# Generated manually to fix avis unique constraint

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservation', '0026_merge_0024_alter_tarif_created_at_0024_bien_tags_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='avis',
            unique_together={('user', 'bien')},
        ),
    ]
