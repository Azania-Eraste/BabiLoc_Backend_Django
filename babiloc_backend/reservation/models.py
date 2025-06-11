from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator,MaxValueValidator
from decimal import Decimal
from enum import Enum

User = get_user_model()

class Typetarif(Enum):
    JOURNALIER = "Journalier"
    HEBDOMADAIRE = "Hebdomadaire"
    MENSUEL = "Mensuel"
    BIMENSUEL = "Bimensuel"
    TRIMESTRIEL = "Trimensuel"
    SEMESTRIEL = "Semestriel"
    ANNUEL = "Annuel"


class Type_Bien(models.Model):
    
    nom = models.CharField(max_length=250)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return self.nom


class Bien(models.Model):
    
    nom = models.CharField(max_length=250)
    description = models.TextField()
    noteGlobale = models.FloatField(
        validators=[
            MinValueValidator(0.0),      # valeur minimale
            MaxValueValidator(5.0)   # valeur maximale
        ]
    ) 
    owner = models.ForeignKey( 
        User, 
        on_delete=models.CASCADE, 
        related_name='Propriétaire_bien',
        verbose_name="Propriétaire"
        )
    disponibility = models.BooleanField()
    type_bien = models.ForeignKey(Type_Bien, related_name="biens", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def get_first_image(self):
        return self.medias.first().image.url if self.medias.exists() else None


    def __str__(self):
        return self.nom


class Tarif(models.Model):

    nom = models.CharField(max_length=250)
    prix = models.FloatField(validators=[MinValueValidator(0.0)])
    type_tarif = models.CharField(max_length=50, choices=[(tag.name, tag.value) for tag in Typetarif], null=True)
    bien = models.ForeignKey(Bien,on_delete=models.CASCADE, related_name='Tarifs_Biens_id')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé  le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return self.nom

class Media(models.Model):
    bien = models.ForeignKey('Bien', on_delete=models.CASCADE, related_name='medias')
    image = models.ImageField(upload_to='biens/')

    def __str__(self):
        return f"Image pour {self.bien.titre}"

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
        ('completed', 'Terminée'),
    ]
    
    annonce_id = models.ForeignKey(Bien,on_delete=models.CASCADE, related_name='Reservation_Bien_ids')
    
    frais_service_percent = Decimal("0.15")

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reservations',
        verbose_name="Utilisateur"
    )
    
    date_debut = models.DateTimeField(verbose_name="Date de début")
    date_fin = models.DateTimeField(verbose_name="Date de fin")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Statut"
    )
    prix_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Prix total"
    )
    
    message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message du client"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
    
    def __str__(self):
        return f"Reservation #{self.id} - {self.user.username}"
    
    @property
    def duree_jours(self):
        """Calcule la durée en jours"""
        return (self.date_fin - self.date_debut).days
    
    @property
    def frais_service(self):
        return round(self.prix_total * self.frais_service_percent, 2)

    @property
    def revenu_net_hote(self):
        return round(self.prix_total - self.frais_service, 2)
    