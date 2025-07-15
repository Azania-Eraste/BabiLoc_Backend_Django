# Generated migration for parrainage system

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('Auths', '0008_alter_customuser_email'),
    ]

    operations = [
        # Ajouter les nouveaux champs au modèle CustomUser
        migrations.AddField(
            model_name='customuser',
            name='date_parrainage',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date de parrainage'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='parrainage_actif',
            field=models.BooleanField(default=True, verbose_name='Parrainage actif'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='points_parrainage',
            field=models.IntegerField(default=0, verbose_name='Points de parrainage'),
        ),
        
        # Créer le modèle HistoriqueParrainage
        migrations.CreateModel(
            name='HistoriqueParrainage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_action', models.CharField(choices=[('parrainage', 'Parrainage'), ('recompense', 'Récompense'), ('bonus', 'Bonus'), ('utilisation_code', 'Utilisation de code promo')], max_length=20, verbose_name="Type d'action")),
                ('montant_recompense', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Montant récompense')),
                ('points_recompense', models.IntegerField(default=0, verbose_name='Points récompense')),
                ('description', models.TextField(verbose_name='Description')),
                ('statut_recompense', models.CharField(choices=[('en_attente', 'En attente'), ('versee', 'Versée'), ('annulee', 'Annulée')], default='en_attente', max_length=20, verbose_name='Statut récompense')),
                ('date_action', models.DateTimeField(auto_now_add=True, verbose_name='Date action')),
                ('date_recompense', models.DateTimeField(blank=True, null=True, verbose_name='Date récompense')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('filleul', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='historique_filleul', to=settings.AUTH_USER_MODEL, verbose_name='Filleul')),
                ('parrain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historiques_parrainage', to=settings.AUTH_USER_MODEL, verbose_name='Parrain')),
            ],
            options={
                'verbose_name': 'Historique de parrainage',
                'verbose_name_plural': 'Historiques de parrainage',
                'ordering': ['-created_at'],
            },
        ),
        
        # Créer le modèle CodePromoParrainage
        migrations.CreateModel(
            name='CodePromoParrainage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='Code promo')),
                ('pourcentage_reduction', models.DecimalField(decimal_places=2, default=10.0, max_digits=5, verbose_name='Pourcentage de réduction')),
                ('reduction_percent', models.DecimalField(decimal_places=2, default=10.0, max_digits=5, verbose_name='Réduction (%)')),
                ('montant_reduction', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Montant réduction fixe')),
                ('montant_min', models.DecimalField(decimal_places=2, default=50000.0, max_digits=10, verbose_name='Montant minimum')),
                ('nombre_utilisations_max', models.IntegerField(default=1, verbose_name="Nombre d'utilisations max")),
                ('nombre_utilisations', models.IntegerField(default=0, verbose_name="Nombre d'utilisations")),
                ('date_expiration', models.DateTimeField(verbose_name="Date d'expiration")),
                ('utilise', models.BooleanField(default=False, verbose_name='Utilisé')),
                ('est_actif', models.BooleanField(default=True, verbose_name='Actif')),
                ('date_utilisation', models.DateTimeField(blank=True, null=True, verbose_name="Date d'utilisation")),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='Date création')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('parrain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='codes_promo_parrainage', to=settings.AUTH_USER_MODEL, verbose_name='Parrain')),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='codes_promo_crees', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur créateur')),
                ('utilise_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='codes_promo_utilises', to=settings.AUTH_USER_MODEL, verbose_name='Utilisé par')),
            ],
            options={
                'verbose_name': 'Code promo parrainage',
                'verbose_name_plural': 'Codes promo parrainage',
                'ordering': ['-created_at'],
            },
        ),
    ]
