from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator,MaxValueValidator
from decimal import Decimal
from enum import Enum
from django.db.models import TextChoices
from django.utils import timezone
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from django.core.files.base import ContentFile
from io import BytesIO
import os

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
    RESERVATION = "reservation", "Réservation"
    REMBOURSEMENT = "remboursement", "Remboursement"
    COMMISSION = "commission", "Commission"
    EN_ATTENTE = "en_attente", "En attente"
    INITIALISATION = "initialisation", "Initialisation"
    ANNULATION = "annulation", "Annulation"


class TagBien(models.Model):
    nom = models.CharField(max_length=100, unique=True)  # Ex: "Vue mer", "Proche transport"
    description = models.TextField(blank=True, null=True)  # Description optionnelle du tag
    iconName = models.CharField(max_length=100, blank=True, null=True)  # Nom de l'icône associée (optionnel)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return self.nom


# ============================================================================
# MODÈLE TYPE_BIEN
# ============================================================================
# Représente les différents types de biens immobiliers disponibles à la location
# Exemples : Appartement, Maison, Studio, Villa, Chambre, Bureau, etc.
# Un type peut avoir plusieurs biens associés (relation One-to-Many)
class Type_Bien(models.Model):
    
    nom = models.CharField(max_length=250)  # Ex: "Appartement", "Villa"
    description = models.TextField()  # Description détaillée du type
    tags = models.ManyToManyField(TagBien, related_name="types_bien", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return self.nom



# ============================================================================
# MODÈLE BIEN
# ============================================================================
# Représente un bien immobilier mis en location sur la plateforme
# Exemple : "Appartement 2 pièces à Cocody" avec propriétaire, note, disponibilité
# Chaque bien appartient à un propriétaire et a un type spécifique
class Ville(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    pays = models.CharField(max_length=100, default="Côte d'Ivoire")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        verbose_name = "Ville"
        verbose_name_plural = "Villes"
        ordering = ['nom']

    def __str__(self):
        return self.nom

class Bien(models.Model):
    
    class TypeCarburant(models.TextChoices):
        ESSENCE = 'essence', 'Essence'
        DIESEL = 'diesel', 'Diesel'
        ELECTRIQUE = 'electrique', 'Électrique'
        HYBRIDE = 'hybride', 'Hybride'

    class TypeTransmission(models.TextChoices):
        MANUELLE = 'manuelle', 'Manuelle'
        AUTOMATIQUE = 'automatique', 'Automatique'
        SEMI_AUTOMATIQUE = 'semi_automatique', 'Semi-automatique'
    
    nom = models.CharField(max_length=250)  # Ex: "Villa moderne 4 chambres"
    description = models.TextField()  # Description complète du bien
    ville = models.ForeignKey(Ville, on_delete=models.SET_NULL, null=True, blank=True, related_name="biens", verbose_name="Ville")
    
    noteGlobale = models.FloatField(  # Note moyenne sur 5 étoiles
        validators=[
            MinValueValidator(0.0),      # Note minimale : 0/5
            MaxValueValidator(5.0)       # Note maximale : 5/5
        ]
    ) 
    vues = models.PositiveIntegerField(default=0)  # ➤ Nouveau champ
    owner = models.ForeignKey(  # Propriétaire du bien
        User, 
        on_delete=models.CASCADE, 
        related_name='Propriétaire_bien',
        verbose_name="Propriétaire"
        )
    disponibility = models.BooleanField()  # True = disponible, False = occupé
    type_bien = models.ForeignKey(Type_Bien, related_name="biens", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    chauffeur = models.BooleanField(default=False, verbose_name="Chauffeur inclus", help_text="Indique si un chauffeur est inclus avec le bien")
    prix_chauffeur = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Prix du chauffeur",
        help_text="Prix supplémentaire pour le service de chauffeur"
    )

    # Exemple de champ spécifique à un véhicule
    marque = models.CharField(max_length=100, null=True, blank=True)
    modele = models.CharField(max_length=100, null=True, blank=True)
    plaque = models.CharField(max_length=20, null=True, blank=True)
    nb_places = models.IntegerField(null=True, blank=True)
    carburant = models.CharField(
        max_length=20,
        choices=TypeCarburant.choices,
        null=True,
        blank=True,
        verbose_name="Type de carburant"
    )
    transmission = models.CharField(
        max_length=20,
        choices=TypeTransmission.choices,
        null=True,
        blank=True,
        verbose_name="Type de transmission"
    )

    # Exemple pour une maison
    nb_chambres = models.IntegerField(null=True, blank=True)
    has_piscine = models.BooleanField(null=True, blank=True)

    est_verifie = models.BooleanField(default=False)

    def get_first_image(self):
        """Récupère la première image du bien pour l'affichage en liste"""
        return self.media.first().image.url if self.media.exists() else None

    def nombre_likes(self):
        return self.favoris.count()

    def __str__(self):
        return self.nom

class DisponibiliteHebdo(models.Model):
    JOUR_CHOICES = [
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
        ('dimanche', 'Dimanche'),
    ]

    bien = models.OneToOneField('Bien', related_name='disponibilite_hebdo', on_delete=models.CASCADE)
    jours = models.JSONField(default=list, help_text="Ex: ['lundi', 'mardi', 'jeudi']")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        verbose_name = "Disponibilité Hebdomadaire"
        verbose_name_plural = "Disponibilités Hebdomadaires"

    def __str__(self):
        return f"{self.bien.nom} disponible les {', '.join(self.jours)}"


class Document(models.Model):
    bien = models.ForeignKey("Bien", related_name="documents", on_delete=models.CASCADE)
    nom = models.CharField(max_length=255)  # Exemple: "Carte Grise", "Attestation de propriété"
    fichier = models.FileField(upload_to='documents_biens/', blank=True, null=True)
    image = models.ImageField(upload_to='documents_biens/images/', blank=True, null=True)
    type = models.CharField(
        max_length=100,
        choices=[
            ('carte_grise', 'Carte Grise'),
            ('assurance', 'Assurance'),
            ('attestation_propriete', 'Attestation de propriété'),
            ('autre', 'Autre'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    date_upload = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Validation pour s'assurer qu'au moins un fichier ou une image est fourni"""
        from django.core.exceptions import ValidationError
        if not self.fichier and not self.image:
            raise ValidationError('Vous devez fournir soit un fichier soit une image.')
        
        if self.fichier and self.image:
            raise ValidationError('Vous ne pouvez pas fournir à la fois un fichier et une image.')

    def get_file_url(self):
        """Retourne l'URL du fichier ou de l'image"""
        if self.fichier:
            return self.fichier.url
        elif self.image:
            return self.image.url
        return None

    def get_file_type(self):
        """Retourne le type de fichier (document ou image)"""
        if self.fichier:
            return 'document'
        elif self.image:
            return 'image'
        return None

    def get_file_extension(self):
        """Retourne l'extension du fichier"""
        if self.fichier:
            return self.fichier.name.split('.')[-1].lower()
        elif self.image:
            return self.image.name.split('.')[-1].lower()
        return None

    def __str__(self):
        return f"{self.nom} pour {self.bien.nom}"

# ============================================================================
# MODÈLE TARIF
# ============================================================================
# Définit les prix de location pour chaque bien selon différentes périodes
# Exemples : "Prix par jour: 25000 FCFA", "Prix par semaine: 150000 FCFA"
# Un bien peut avoir plusieurs tarifs (journalier, hebdomadaire, mensuel)
class Tarif(models.Model):

    prix = models.FloatField(validators=[MinValueValidator(0.0)])
    type_tarif = models.CharField(max_length=50, choices=[(tag.name, tag.value) for tag in Typetarif], null=True)
    bien = models.ForeignKey(Bien,on_delete=models.CASCADE, related_name='tarifs')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé  le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    

    def __str__(self):
        return f"{self.type_tarif} - {self.bien.nom}"


# ============================================================================
# MODÈLE MEDIA
# ============================================================================
# Stocke les images/photos associées à chaque bien immobilier
# Exemple : Photos de la façade, salon, chambres, cuisine, etc.
# Un bien peut avoir plusieurs images pour le présenter aux locataires
class Media(models.Model):
    bien = models.ForeignKey('Bien', on_delete=models.CASCADE, related_name='media')
    image = models.ImageField(upload_to='biens/')  # Images stockées dans media/biens/

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return f"Image pour {self.bien.nom}"  # Correction: utiliser 'nom' au lieu de 'titre'


# ============================================================================
# MODÈLE RESERVATION
# ============================================================================
# Représente une demande de réservation d'un bien par un utilisateur
# Exemple : "Jean réserve la Villa à Cocody du 15/01 au 20/01 pour 125000 FCFA"
# Gère le cycle de vie : En attente → Confirmée → Terminée ou Annulée
class Reservation(models.Model):
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="Confirmée le")
    
    # Renommer annonce_id en bien
    bien = models.ForeignKey(Bien, on_delete=models.CASCADE, related_name='reservations')
    
    # Commission de la plateforme (15%)
    commission_percent = Decimal("0.15")
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
        ('completed', 'Terminée'),
    ]

    type_tarif = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in Typetarif],
        default=Typetarif.JOURNALIER.name,
        verbose_name="Type de tarif"
    )
    
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
    prix_total = models.DecimalField(  # Prix total calculé pour la période
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Prix total"
    )
    
    message = models.TextField(  # Message optionnel du client au propriétaire
        blank=True,
        null=True,
        verbose_name="Message du client"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        ordering = ['-created_at']  # Réservations les plus récentes en premier
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
    
    def __str__(self):
        return f"Reservation #{self.id} - {self.user.username}"
    
    @property
    def duree_jours(self):
        """Calcule la durée du séjour en jours"""
        return (self.date_fin - self.date_debut).days
    
    @property
    def commission_plateforme(self):
        """Commission de 15% gardée par la plateforme"""
        return round(self.prix_total * self.commission_percent, 2)

    @property
    def revenu_proprietaire(self):
        """85% du prix total pour le propriétaire"""
        return round(self.prix_total * (Decimal("1") - self.commission_percent), 2)
    
    @property
    def frais_service(self):
        """Alias pour commission_plateforme (compatibilité)"""
        return self.commission_plateforme

    @property
    def revenu_net_hote(self):
        """Alias pour revenu_proprietaire (compatibilité)"""
        return self.revenu_proprietaire
    
    def save(self, *args, **kwargs):
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        super().save(*args, **kwargs)

    def get_tarif_bien(self):
        """Récupère le tarif du bien selon le type choisi"""
        return self.bien.Tarifs_Biens_id.filter(type_tarif=self.type_tarif).first()
    
    def save(self, *args, **kwargs):
        # Only calculate price for new reservations
        if not self.pk and not self.prix_total:
            tarif = self.get_tarif_bien()
            if tarif:
                nb_jours = (self.date_fin - self.date_debut).days or 1
                self.prix_total = Decimal(tarif.prix) * Decimal(nb_jours)
            else:
                # Instead of raising an error, provide a more helpful message
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Aucun tarif '{self.type_tarif}' trouvé pour le bien '{self.bien.nom}'. "
                    f"Veuillez contacter le propriétaire ou choisir un autre type de tarif."
                )
        
        # Update confirmation time
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        # S’il s’agit d’une nouvelle réservation, calcule le prix
        if not self.pk:
            tarif = self.get_tarif_bien()
            if tarif:
                nb_jours = (self.date_fin - self.date_debut).days or 1
                self.prix_total = Decimal(tarif.prix) * Decimal(nb_jours)
            else:
                raise ValueError("Aucun tarif trouvé pour ce bien et ce type de tarif.")
        
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        
        super().save(*args, **kwargs)


class CodePromo(models.Model):
    nom = models.CharField(unique=True)
    reduction = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.0')),
            MaxValueValidator(Decimal('0.5'))
        ]
    )
    reservations = models.ManyToManyField(
        "Reservation",
        related_name="codes_promos",
        blank=True,
        help_text="Réservations qui ont utilisé ce code promo"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return f"{self.nom} - {int(self.reduction * 100)}%"


class HistoriqueStatutReservation(models.Model):
    reservation = models.ForeignKey('Reservation', on_delete=models.CASCADE, related_name='historiques_statut')
    ancien_statut = models.CharField(max_length=50, choices=StatutReservation.choices)
    nouveau_statut = models.CharField(max_length=50, choices=StatutReservation.choices)
    date_changement = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

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
    # Status choices
    STATUT_PENDING = 'pending'
    STATUT_EFFECTUE = 'effectue'
    STATUT_ECHEC = 'echec'
    STATUT_REMBOURSE = 'rembourse'
    
    STATUT_CHOICES = [
        (STATUT_PENDING, 'En attente'),
        (STATUT_EFFECTUE, 'Effectué'),
        (STATUT_ECHEC, 'Échoué'),
        (STATUT_REMBOURSE, 'Remboursé'),
    ]
    
    statut_paiement = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_PENDING
    )

    montant = models.FloatField()
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    mode = models.ForeignKey(Mode, on_delete=models.CASCADE, related_name="ModePaiement", null=True, blank=True)  # ✅ Rendre optionnel

    payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    statut = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    type_operation = models.CharField(
        max_length=50,
        choices=TypeOperation.choices,
        verbose_name="Type d'opération"
    )
    
    reservation = models.ForeignKey(
        Reservation, 
        on_delete=models.CASCADE, 
        related_name="paiements", 
        null=True
    )

    # Nouveaux champs pour CinetPay
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_token = models.CharField(max_length=255, null=True, blank=True)
    payment_url = models.URLField(null=True, blank=True)
    cinetpay_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'reservation_paiement'
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def enregistrer_historique(self, type_op, montant=None, description=None):
        HistoriquePaiement.objects.create(
            paiement=self,
            utilisateur=self.utilisateur,
            type_operation=type_op,
            montant=montant if montant is not None else self.montant,
            description=description
        )

    def effectuer_paiement(self):
        if self.mode and self.mode.type_paiement == "Liquide":  # ✅ Vérifier que mode existe
            self.statut_paiement = StatutPaiement.EFFECTUE
            self.save()
            return True
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
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

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



# ============================================================================
# MODÈLE FAVORI
# ============================================================================
# Permet aux utilisateurs de sauvegarder leurs biens préférés
# Exemple : "Marie a ajouté l'Appartement Plateau aux favoris"
# Système de wishlist pour retrouver facilement les biens qui intéressent
class Favori(models.Model):
    user = models.ForeignKey(  # Utilisateur qui ajoute aux favoris
        User, 
        on_delete=models.CASCADE, 
        related_name='favoris',
        verbose_name="Utilisateur"
    )
    bien = models.ForeignKey(  # Bien ajouté aux favoris
        Bien, 
        on_delete=models.CASCADE, 
        related_name='favoris',
        verbose_name="Bien"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        # Un utilisateur ne peut pas ajouter le même bien deux fois
        unique_together = ('user', 'bien')  
        ordering = ['-created_at']  # Favoris les plus récents en premier
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
    
    def __str__(self):
        return f"{self.user.username} - {self.bien.nom}"
    

@receiver(post_save, sender=Document)
def send_document_email(sender, instance, created, **kwargs):
    if created:
        subject = f"Nouveau document soumis : {instance.nom}"
        message = f"""
Bonjour,

Un nouveau document a été soumis pour le bien : {instance.bien.nom}.

Détails :
- Type : {instance.get_type_display()}
- Nom du fichier : {instance.fichier.name}
- Propriétaire : {instance.bien.owner.get_full_name() or instance.bien.owner.username}

Veuillez le vérifier en pièce jointe.

Merci.
        """

        email = EmailMessage(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [settings.EMAIL_HOST_USER,],  # Change ça par l'adresse du modérateur
        )

        # Ajoute le fichier
        if instance.fichier:
            email.attach_file(instance.fichier.path)

        email.send(fail_silently=False)


class Avis(models.Model):
    """
    Modèle pour gérer les avis et notes des utilisateurs sur les biens
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='avis_donnes',
        verbose_name="Utilisateur"
    )
    bien = models.ForeignKey(
        Bien, 
        on_delete=models.CASCADE, 
        related_name='avis',
        verbose_name="Bien"
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='avis',
        verbose_name="Réservation",
        help_text="L'avis est lié à une réservation spécifique"
    )
    
    # Note sur 5 étoiles
    note = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        verbose_name="Note (1-5 étoiles)"
    )
    
    # Commentaire détaillé
    commentaire = models.TextField(
        max_length=1000,
        verbose_name="Commentaire"
    )
    
    # Notes détaillées par catégorie
    note_proprete = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Propreté",
        null=True, blank=True
    )
    note_communication = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Communication",
        null=True, blank=True
    )
    note_emplacement = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Emplacement",
        null=True, blank=True
    )
    note_rapport_qualite_prix = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Rapport qualité/prix",
        null=True, blank=True
    )
    
    # Recommandation
    recommande = models.BooleanField(
        default=True,
        verbose_name="Recommande ce bien"
    )
    
    # Statut de l'avis
    est_valide = models.BooleanField(
        default=True,
        verbose_name="Avis validé"
    )
    
    # Réponse du propriétaire
    reponse_proprietaire = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Réponse du propriétaire"
    )
    date_reponse = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de réponse"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        # Un utilisateur ne peut donner qu'un seul avis par réservation
        unique_together = ('user', 'reservation')
        ordering = ['-created_at']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
    
    def __str__(self):
        return f"Avis de {self.user.username} sur {self.bien.nom} - {self.note}⭐"
    
    @property
    def note_moyenne_detaillee(self):
        """Calcule la moyenne des notes détaillées"""
        notes = [
            self.note_proprete,
            self.note_communication,
            self.note_emplacement,
            self.note_rapport_qualite_prix
        ]
        notes_valides = [note for note in notes if note is not None]
        if notes_valides:
            return round(sum(notes_valides) / len(notes_valides), 1)
        return None
    
    def clean(self):
        """Validation personnalisée"""
        from django.core.exceptions import ValidationError
        
        # Vérifier que la réservation est terminée
        if self.reservation and self.reservation.status != 'completed':
            raise ValidationError("Vous ne pouvez donner un avis que pour une réservation terminée.")
        
        # Vérifier que l'utilisateur a bien fait cette réservation
        if self.reservation and self.reservation.user != self.user:
            raise ValidationError("Vous ne pouvez donner un avis que pour vos propres réservations.")
        
        # Vérifier que le bien correspond à la réservation
        if self.reservation and self.reservation.annonce_id != self.bien:
            raise ValidationError("Le bien ne correspond pas à la réservation.")

# Signal pour mettre à jour la note globale du bien
@receiver(models.signals.post_save, sender=Avis)
@receiver(models.signals.post_delete, sender=Avis)
def mettre_a_jour_note_globale_bien(sender, instance, **kwargs):
    """Met à jour la note globale du bien après ajout/suppression d'un avis"""
    from django.db.models import Avg
    
    bien = instance.bien
    note_moyenne = bien.avis.filter(est_valide=True).aggregate(
        moyenne=Avg('note')
    )['moyenne']
    
    if note_moyenne:
        bien.noteGlobale = round(note_moyenne, 1)
    else:
        bien.noteGlobale = 0.0
    
    bien.save(update_fields=['noteGlobale'])

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Reservation)
def creer_revenu_proprietaire(sender, instance, created, **kwargs):
    """Créer un enregistrement de revenu quand une réservation est complétée"""
    # Only create RevenuProprietaire when reservation status changes to 'completed'
    if instance.status == 'completed':
        # Check if RevenuProprietaire doesn't already exist
        revenu_existant = RevenuProprietaire.objects.filter(reservation=instance).first()
        if not revenu_existant:
            RevenuProprietaire.objects.create(
                proprietaire=instance.bien.owner,
                reservation=instance,
                montant_brut=instance.prix_total,
                commission_plateforme=instance.commission_plateforme,
                revenu_net=instance.revenu_proprietaire
            )


class RevenuProprietaire(models.Model):
    """Suivi des revenus des propriétaires"""
    
    proprietaire = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='revenus_proprietaire'
    )
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='revenu_proprietaire_record'  # ✅ Change the related_name
    )
    
    montant_brut = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Montant brut (prix total)"
    )
    commission_plateforme = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Commission plateforme (15%)"
    )
    revenu_net = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Revenu net propriétaire (85%)"
    )
    
    status_paiement = models.CharField(
        max_length=20,
        choices=[
            ('en_attente', 'En attente'),
            ('verse', 'Versé'),
            ('bloque', 'Bloqué')
        ],
        default='en_attente'
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_versement = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Revenu Propriétaire"
        verbose_name_plural = "Revenus Propriétaires"
    
    def __str__(self):
        return f"Revenu {self.proprietaire.username} - Réservation #{self.reservation.id}"


# ============================================================================
# MODÈLE FACTURE
# ============================================================================
# Modèle pour les factures électroniques
class Facture(models.Model):
    """Modèle pour les factures électroniques"""
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
        ('remboursee', 'Remboursée'),
    ]
    
    TYPE_FACTURE_CHOICES = [
        ('reservation', 'Facture de réservation'),
        ('commission', 'Facture de commission'),
        ('avoir', 'Avoir (remboursement)'),
    ]
    
    # Identifiants
    numero_facture = models.CharField(max_length=50, unique=True, verbose_name="Numéro de facture")
    type_facture = models.CharField(max_length=20, choices=TYPE_FACTURE_CHOICES, default='reservation')
    
    # Relations
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='factures')
    paiement = models.ForeignKey(Paiement, on_delete=models.CASCADE, related_name='factures', null=True, blank=True)
    
    # Informations client
    client_nom = models.CharField(max_length=255, verbose_name="Nom du client")
    client_email = models.EmailField(verbose_name="Email du client")
    client_telephone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone du client")
    client_adresse = models.TextField(blank=True, verbose_name="Adresse du client")
    
    # Informations hôte
    hote_nom = models.CharField(max_length=255, verbose_name="Nom de l'hôte")
    hote_email = models.EmailField(verbose_name="Email de l'hôte")
    hote_telephone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone de l'hôte")
    
    # Montants
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant HT", default=0.00)
    tva_taux = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, verbose_name="Taux TVA (%)")
    montant_tva = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant TVA")
    montant_ttc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant TTC")
    
    # Commission (pour les hôtes)
    commission_plateforme = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Commission plateforme")
    montant_net_hote = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Montant net hôte")
    
    # Statut et dates
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_emission = models.DateTimeField(auto_now_add=True, verbose_name="Date d'émission")
    date_echeance = models.DateField(verbose_name="Date d'échéance")
    date_paiement = models.DateTimeField(null=True, blank=True, verbose_name="Date de paiement")
    
    # Fichier PDF
    fichier_pdf = models.FileField(upload_to='factures/', null=True, blank=True, verbose_name="Fichier PDF")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_emission']
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
    
    def __str__(self):
        return f"Facture {self.numero_facture} - {self.client_nom}"
    
    def save(self, *args, **kwargs):
        # Générer le numéro de facture si ce n'est pas déjà fait
        if not self.numero_facture:
            self.numero_facture = self.generer_numero_facture()
        
        # Calculer la TVA et le montant TTC
        self.calculer_montants()
        
        super().save(*args, **kwargs)
        
        # Générer le PDF après la sauvegarde
        if not self.fichier_pdf:
            self.generer_pdf()
    
    def generer_numero_facture(self):
        """Génère un numéro de facture unique"""
        from datetime import datetime
        annee = datetime.now().year
        mois = datetime.now().month
        
        # Compter les factures du mois
        nb_factures = Facture.objects.filter(
            date_emission__year=annee,
            date_emission__month=mois
        ).count() + 1
        
        return f"FAC-{annee}{mois:02d}-{nb_factures:04d}"
    
    def calculer_montants(self):
        """Calcule les montants TTC, TVA, etc."""
        if self.reservation:
            # Montant HT = Prix total de la réservation
            self.montant_ht = self.reservation.prix_total
            
            # TVA - Convert tva_taux to Decimal and divide by 100
            self.montant_tva = self.montant_ht * (Decimal(str(self.tva_taux)) / Decimal('100'))
            
            # TTC
            self.montant_ttc = self.montant_ht + self.montant_tva
            
            # Commission et montant net pour l'hôte
            if self.type_facture == 'reservation':
                # Use the @property methods from the Reservation model
                self.commission_plateforme = self.reservation.commission_plateforme
                self.montant_net_hote = self.reservation.revenu_proprietaire  # This is now a @property

    def generer_pdf(self):
        """Génère le fichier PDF de la facture avec ReportLab"""
        try:
            # Créer un buffer pour le PDF
            buffer = BytesIO()
            
            # Créer le document PDF
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2c3e50'),
                alignment=1,  # Centre
                spaceAfter=30,
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#34495e'),
                spaceAfter=12,
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=6,
            )
            
            # En-tête
            story.append(Paragraph("BabiLoc", title_style))
            story.append(Paragraph("Plateforme de location de biens", normal_style))
            story.append(Paragraph("Email: contact@babiloc.com | Tél: +225 XX XX XX XX", normal_style))
            story.append(Spacer(1, 20))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
            story.append(Spacer(1, 20))
            
            # Informations facture
            story.append(Paragraph(f"Facture {self.numero_facture}", heading_style))
            story.append(Paragraph(f"Date d'émission: {self.date_emission.strftime('%d/%m/%Y')}", normal_style))
            story.append(Paragraph(f"Date d'échéance: {self.date_echeance.strftime('%d/%m/%Y')}", normal_style))
            story.append(Paragraph(f"Statut: {self.get_statut_display()}", normal_style))
            if self.date_paiement:
                story.append(Paragraph(f"Date de paiement: {self.date_paiement.strftime('%d/%m/%Y %H:%M')}", normal_style))
            story.append(Spacer(1, 20))
            
            # Informations client et hôte
            client_hote_data = [
                ['Facturé à:', 'Propriétaire:'],
                [self.client_nom, self.hote_nom],
                [self.client_email, self.hote_email],
            ]
            
            if self.client_telephone:
                client_hote_data.append([self.client_telephone, self.hote_telephone or ''])
            
            client_hote_table = Table(client_hote_data, colWidths=[3*inch, 3*inch])
            client_hote_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONT', (0, 1), (-1, 1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            
            story.append(client_hote_table)
            story.append(Spacer(1, 30))
            
            # Détails de la réservation
            story.append(Paragraph("Détails de la réservation", heading_style))
            
            reservation_data = [
                ['Description', 'Période', 'Quantité', 'Prix unitaire', 'Montant HT'],
                [
                    f"Location {self.reservation.bien.nom}",
                    f"Du {self.reservation.date_debut.strftime('%d/%m/%Y')} au {self.reservation.date_fin.strftime('%d/%m/%Y')}",
                    f"{self.reservation.duree_jours} jour(s)",
                    f"{float(self.reservation.prix_total / self.reservation.duree_jours):.0f} FCFA",
                    f"{float(self.montant_ht):.0f} FCFA"
                ]
            ]
            
            reservation_table = Table(reservation_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
            reservation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            story.append(reservation_table)
            story.append(Spacer(1, 20))
            
            # Totaux
            totaux_data = [
                ['Montant HT:', f"{float(self.montant_ht):.0f} FCFA"],
                [f'TVA ({self.tva_taux}%):', f"{float(self.montant_tva):.0f} FCFA"],
                ['Total TTC:', f"{float(self.montant_ttc):.0f} FCFA"],
            ]
            
            totaux_table = Table(totaux_data, colWidths=[2*inch, 1.5*inch])
            totaux_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(totaux_table)
            story.append(Spacer(1, 30))
            
            # Répartition pour l'hôte
            if self.type_facture == 'reservation':
                story.append(Paragraph("Répartition (Information hôte)", heading_style))
                
                repartition_data = [
                    ['Montant total de la réservation:', f"{float(self.montant_ttc):.0f} FCFA"],
                    ['Commission plateforme (15%):', f"{float(self.commission_plateforme):.0f} FCFA"],
                    ['Montant net hôte (85%):', f"{float(self.montant_net_hote):.0f} FCFA"],
                ]
                
                repartition_table = Table(repartition_data, colWidths=[2.5*inch, 1.5*inch])
                repartition_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e8')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                
                story.append(repartition_table)
                story.append(Spacer(1, 30))
            
            # Conditions
            story.append(Paragraph("Conditions de paiement", heading_style))
            story.append(Paragraph("• Paiement effectué via la plateforme BabiLoc", normal_style))
            story.append(Paragraph("• Paiement sécurisé par CinetPay", normal_style))
            story.append(Paragraph("• En cas de litige, contactez notre service client", normal_style))
            story.append(Spacer(1, 40))
            
            # Pied de page
            story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
            story.append(Spacer(1, 10))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=1,  # Centre
            )
            story.append(Paragraph("BabiLoc - Plateforme de location de biens", footer_style))
            story.append(Paragraph("Cette facture est générée automatiquement et ne nécessite pas de signature", footer_style))
            story.append(Paragraph("Merci de votre confiance !", footer_style))
            
            # Construire le PDF
            doc.build(story)
            
            # Sauvegarder le fichier
            buffer.seek(0)
            filename = f"facture_{self.numero_facture}.pdf"
            self.fichier_pdf.save(
                filename,
                ContentFile(buffer.read()),
                save=False
            )
            
            # Mettre à jour sans déclencher save() à nouveau
            Facture.objects.filter(pk=self.pk).update(fichier_pdf=self.fichier_pdf)
            
            buffer.close()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur génération PDF facture {self.numero_facture}: {str(e)}")
    
    def get_lignes_facture(self):
        """Retourne les lignes de la facture"""
        lines = []
        
        if self.type_facture == 'reservation':
            lines.append({
                'description': f"Location {self.reservation.bien.nom}",
                'periode': f"Du {self.reservation.date_debut.strftime('%d/%m/%Y')} au {self.reservation.date_fin.strftime('%d/%m/%Y')}",
                'quantite': self.reservation.duree_jours,
                'unite': 'jour(s)',
                'prix_unitaire': float(self.reservation.prix_total / self.reservation.duree_jours),
                'montant': float(self.montant_ht)
            })
        
        return lines
    
    def envoyer_par_email(self, destinataire_email=None, copie_hote=True):
        """Envoie la facture par email"""
        from django.core.mail import EmailMessage
        from django.conf import settings
        
        if not destinataire_email:
            destinataire_email = self.client_email
        
        # Préparer l'email
        sujet = f"Facture {self.numero_facture} - BabiLoc"
        
        message_text = f"""
Bonjour {self.client_nom},

Nous vous remercions pour votre réservation sur BabiLoc. Votre facture est maintenant disponible.

Détails de la facture :
- Numéro de facture : {self.numero_facture}
- Date d'émission : {self.date_emission.strftime('%d/%m/%Y')}
- Bien loué : {self.reservation.bien.nom}
- Période : du {self.reservation.date_debut.strftime('%d/%m/%Y')} au {self.reservation.date_fin.strftime('%d/%m/%Y')}
- Durée : {self.reservation.duree_jours} jour(s)
- Montant total : {self.montant_ttc} FCFA

Vous trouverez votre facture en pièce jointe au format PDF.

Cordialement,
L'équipe BabiLoc

---
BabiLoc - Plateforme de location de biens
Email: contact@babiloc.com | Tél: +225 XX XX XX XX
        """
        
        # Destinataires
        destinataires = [destinataire_email]
        if copie_hote and self.hote_email:
            destinataires.append(self.hote_email)
        
        # Créer l'email
        email = EmailMessage(
            subject=sujet,
            body=message_text,
            from_email=settings.EMAIL_HOST_USER,
            to=destinataires,
        )
        
        # Attacher le PDF
        if self.fichier_pdf:
            try:
                email.attach_file(self.fichier_pdf.path)
            except:
                # Si le fichier n'existe pas, le régénérer
                self.generer_pdf()
                if self.fichier_pdf:
                    email.attach_file(self.fichier_pdf.path)
        
        # Envoyer
        try:
            email.send()
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur envoi email facture {self.numero_facture}: {str(e)}")
            return False

# Signal pour créer automatiquement une facture lors du paiement
@receiver(post_save, sender=Paiement)
def creer_facture_automatique(sender, instance, created, **kwargs):
    """Crée automatiquement une facture quand un paiement est effectué"""
    if instance.statut_paiement == StatutPaiement.EFFECTUE and instance.reservation:
        # Vérifier si une facture n'existe pas déjà
        facture_existante = Facture.objects.filter(
            reservation=instance.reservation,
            paiement=instance
        ).first()
        
        if not facture_existante:
            # Créer la facture
            facture = Facture.objects.create(
                reservation=instance.reservation,
                paiement=instance,
                client_nom=f"{instance.utilisateur.first_name} {instance.utilisateur.last_name}".strip() or instance.utilisateur.username,
                client_email=instance.utilisateur.email,
                client_telephone=getattr(instance.utilisateur, 'number', ''),
                hote_nom=f"{instance.reservation.bien.owner.first_name} {instance.reservation.bien.owner.last_name}".strip() or instance.reservation.bien.owner.username,
                hote_email=instance.reservation.bien.owner.email,
                hote_telephone=getattr(instance.reservation.bien.owner, 'number', ''),
                date_echeance=timezone.now().date(),
                date_paiement=instance.date_paiement or timezone.now(),
                statut='payee'
            )
            
            # Envoyer par email
            facture.envoyer_par_email()