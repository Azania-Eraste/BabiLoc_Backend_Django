from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator,MaxValueValidator
from decimal import Decimal
from enum import Enum
from django.db.models import TextChoices
from django.utils import timezone
from django.db.models.signals import pre_save
from django.dispatch import receiver

User = get_user_model()

class StatutReservation(TextChoices):
    EN_ATTENTE = "pending","En attente"
    CONFIRMED = "confirmed","Confirmée"
    CANCELLED = "cancelled","Annulée"
    COMPLETED = 'completed', 'Terminée'
class Typetarif(Enum):
    JOURNALIER = "Journalier"
    HEBDOMADAIRE = "Hebdomadaire"
    MENSUEL = "Mensuel"
    BIMENSUEL = "Bimensuel"
    TRIMESTRIEL = "Trimensuel"
    SEMESTRIEL = "Semestriel"
    ANNUEL = "Annuel"

class TypePaiement(TextChoices):
    MOBILE_MONEY = 'MOBILE_MONEY','Mobile Money'
    CREDIT_CARD = 'CREDIT_CARD','Carte de crédit/débit'
    PREPAID_CARD = 'PREPAID_CARD','Carte prépayée'
    LIQUIDE = 'LIQUIDE','Liquide'



class StatutPaiement(TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    EFFECTUE = "effectue", "Effectué"
    ECHOUE = "echoue", "Échoué"


class TypeOperation(TextChoices):
    RESERVATION = 'reservation', 'Réservation confirmée'
    EN_ATTENTE = 'en_attente', 'Paiement en attente'
    FRAIS = 'frais', 'Frais de service'
    RETRAIT = 'retrait', 'Retrait'


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


    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="Confirmée le")
    
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
        choices=StatutReservation, 
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
    
    def save(self, *args, **kwargs):
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        super().save(*args, **kwargs)

class HistoriqueStatutReservation(models.Model):
    reservation = models.ForeignKey('Reservation', on_delete=models.CASCADE, related_name='historiques_statut')
    ancien_statut = models.CharField(max_length=50, choices=StatutReservation.choices)
    nouveau_statut = models.CharField(max_length=50, choices=StatutReservation.choices)
    date_changement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reservation {self.reservation.id} : {self.ancien_statut} → {self.nouveau_statut}"


class Mode(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    nom = models.CharField(max_length=255)  # Ex: "Wave", "Carte de crédit/débit"
    description = models.TextField(blank=True, null=True)
    type_paiement = models.CharField(
        max_length=20,
        choices=TypePaiement.choices,
        default=TypePaiement.MOBILE_MONEY
    )
    numero_tel = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=255, blank=True, null=True)
    expiration = models.CharField(max_length=6, blank=True, null=True)
    code = models.CharField(max_length=6, blank=True, null=True)

    statut = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom} - {self.utilisateur.username}"

    class Meta:
        verbose_name = "Mode de paiement"
        verbose_name_plural = "Modes de paiement"

class Paiement(models.Model):
    montant = models.FloatField()
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    mode = models.ForeignKey(Mode, on_delete=models.CASCADE, related_name="ModePaiement")
    
    statut_paiement = models.CharField(
        max_length=20,
        choices=StatutPaiement.choices,
        default=StatutPaiement.EN_ATTENTE,
        verbose_name="Statut du paiement"
    )

    payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    statut = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    type_operation = models.CharField(
        max_length=50,
        choices=TypeOperation.choices,
        verbose_name="Type d’opération"
    )
    
    reservation = models.ForeignKey(
        Reservation, 
        on_delete=models.CASCADE, 
        related_name="paiements", 
        null=True
    )

    def enregistrer_historique(self, type_op, montant=None, description=None):
        HistoriquePaiement.objects.create(
            paiement=self,
            utilisateur=self.utilisateur,
            type_operation=type_op,
            montant=montant if montant is not None else self.montant,
            description=description
        )


    def effectuer_paiement(self):
        if self.mode.type_paiement == "Liquide":
            print(f"Avant mise à jour statut_paiement : {self.statut_paiement}")
            self.statut_paiement = StatutPaiement.EFFECTUE
            self.save()
            print(f"Après sauvegarde : {self.statut_paiement}")
            return True
        print(f"Mode de paiement non éligible pour effectuer_paiement : {self.mode.type_paiement}")
        return False

    def __str__(self):
        return f"Paiement N{self.pk} - Réservation {self.reservation.id if self.reservation else 'N/A'}"

class HistoriquePaiement(models.Model):
    paiement = models.ForeignKey(Paiement, on_delete=models.CASCADE, related_name="historiques")
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    
    type_operation = models.CharField(
        max_length=50,
        choices=TypeOperation.choices,
        verbose_name="Type d’opération"
    )

    montant = models.FloatField(validators=[MinValueValidator(0.0)])
    description = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_operation_display()} - {self.montant} F - {self.utilisateur.username}"
    

@receiver(pre_save, sender=Reservation)
def sauvegarder_historique_statut(sender, instance, **kwargs):
    if not instance.pk:
        # Nouvelle réservation, pas besoin d'historique
        return
    
    ancienne = Reservation.objects.get(pk=instance.pk)
    if ancienne.status != instance.status:
        HistoriqueStatutReservation.objects.create(
            reservation=instance,
            ancien_statut=ancienne.status,
            nouveau_statut=instance.status
        )
