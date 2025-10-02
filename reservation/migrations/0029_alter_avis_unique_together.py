# Generated manually to fix avis unique constraint

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservation', '0028_bienimage'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='avis',
            unique_together={('user', 'bien')},
        ),
    ]
