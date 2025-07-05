from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('reservation', '0007_avis'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reservation',
            old_name='annonce_id',
            new_name='bien',
        ),
    ]