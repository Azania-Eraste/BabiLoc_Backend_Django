# Generated manually to fix reservation model
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservation', '0005_favori'),
    ]

    operations = [
        # Ajouter les nouveaux champs au modèle Bien
        migrations.AddField(
            model_name='bien',
            name='prix',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Prix'),
        ),
        migrations.AddField(
            model_name='bien',
            name='ville',
            field=models.CharField(default='Abidjan', max_length=100, verbose_name='Ville'),
        ),
        
        # Supprimer l'ancien champ annonce_id
        migrations.RemoveField(
            model_name='reservation',
            name='annonce_id',
        ),
        
        # Ajouter le nouveau champ annonce avec une valeur par défaut valide
        migrations.AddField(
            model_name='reservation',
            name='annonce',
            field=models.ForeignKey(
                null=True,  # Permettre NULL temporairement
                on_delete=django.db.models.deletion.CASCADE, 
                related_name='reservations', 
                to='reservation.bien', 
                verbose_name='Bien réservé'
            ),
        ),
    ]
