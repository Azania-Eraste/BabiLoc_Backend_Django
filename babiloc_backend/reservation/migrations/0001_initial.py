# Generated by Django 5.2.1 on 2025-06-03 15:02

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('annonce_id', models.IntegerField()),
                ('date_debut', models.DateTimeField()),
                ('date_fin', models.DateTimeField()),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('confirmed', 'Confirmée'), ('cancelled', 'Annulée'), ('completed', 'Terminée')], default='pending', max_length=20)),
                ('prix_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
