from django.db import models
from Auths.utils import bien_image_upload_to  # <- [`Auths.utils.bien_image_upload_to`](Auths/utils.py)
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator,MaxValueValidator
from decimal import Decimal
from enum import Enum
from django.db.models import TextChoices
from django.utils import timezone
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.mail import EmailMessage, EmailMultiAlternatives
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
from django.utils.html import strip_tags

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
# MODÈLE VILLE
# ============================================================================
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

# ============================================================================
# MODÈLE BIEN
# ============================================================================
# Représente un bien immobilier mis en location sur la plateforme
# Exemple : "Appartement 2 pièces à Cocody" avec propriétaire, note, disponibilité
# Chaque bien appartient à un propriétaire et a un type spécifique
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
    vues = models.PositiveIntegerField(default=0)  # Nombre de vues
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

    # Relation Many-to-Many avec les tags
    tags = models.ManyToManyField(TagBien, related_name="biens", blank=True)

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
    
    # Équipements et services
    has_wifi = models.BooleanField(default=False, verbose_name="WiFi disponible")
    has_parking = models.BooleanField(default=False, verbose_name="Parking disponible")
    has_kitchen = models.BooleanField(default=False, verbose_name="Cuisine équipée")
    has_security = models.BooleanField(default=False, verbose_name="Sécurité/Gardien")
    has_garden = models.BooleanField(default=False, verbose_name="Jardin/Espace vert")

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
    heure_debut = models.TimeField(null=True, blank=True, help_text="Heure de début de disponibilité (ex: 09:00)")
    heure_fin = models.TimeField(null=True, blank=True, help_text="Heure de fin de disponibilité (ex: 18:00)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        verbose_name = "Disponibilité Hebdomadaire"
        verbose_name_plural = "Disponibilités Hebdomadaires"

    def __str__(self):
        horaires = ""
        if self.heure_debut and self.heure_fin:
            horaires = f" de {self.heure_debut.strftime('%H:%M')} à {self.heure_fin.strftime('%H:%M')}"
        return f"{self.bien.nom} disponible les {', '.join(self.jours)}{horaires}"

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
    bien = models.ForeignKey(Bien, on_delete=models.CASCADE, related_name='tarifs')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    def __str__(self):
        return f"{self.type_tarif} - {self.bien.nom}"

    @staticmethod
    def get_tarif_for_bien_and_type(bien, type_tarif):
        """
        Récupère le tarif d'un bien pour un type_tarif donné.
        Retourne l'objet Tarif ou None si non trouvé.
        """
        return Tarif.objects.filter(bien=bien, type_tarif=type_tarif).first()

# ============================================================================
# MODÈLE MEDIA
# ============================================================================
# Stocke les images/photos associées à chaque bien immobilier
# Exemple : Photos de la façade, salon, chambres, cuisine, etc.
# Un bien peut avoir plusieurs images pour le présenter aux locataires
class Media(models.Model):
    TYPE_MEDIA_CHOICES = [
        ('principale', 'Image principale'),
        ('galerie', 'Image de galerie'),
    ]
    
    bien = models.ForeignKey('Bien', on_delete=models.CASCADE, related_name='media')
    type_media = models.CharField(
        max_length=20, 
        choices=TYPE_MEDIA_CHOICES, 
        default='galerie',
        verbose_name="Type de média"
    )
    image = models.ImageField(upload_to='biens/')  # Images stockées dans media/biens/

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Média"
        verbose_name_plural = "Médias"

    def __str__(self):
        return f"{self.get_type_media_display()} pour {self.bien.nom}"

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

    def get_tarif_bien(self):
        """Récupère le tarif du bien selon le type choisi"""
        return self.bien.tarifs.filter(type_tarif=self.type_tarif).first()
    
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

# ============================================================================
# SIGNAL POUR ENVOYER UN EMAIL LORS DU TÉLÉCHARGEMENT DE DOCUMENT
# ============================================================================
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

# ============================================================================
# MODÈLE AVIS
# ============================================================================
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
        # Un utilisateur ne peut donner qu'un seul avis par bien
        unique_together = ('user', 'bien')
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
        if self.reservation and self.reservation.bien != self.bien:
            raise ValidationError("Le bien ne correspond pas à la réservation.")

# ============================================================================
# SIGNAL POUR METTRE À JOUR LA NOTE GLOBALE DU BIEN
# ============================================================================
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

# ============================================================================
# SIGNAL POUR HISTORIQUE DES STATUTS DE RÉSERVATION
# ============================================================================
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
# MODÈLE REVENU PROPRIÉTAIRE
# ============================================================================
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
        related_name='revenu_proprietaire_record'
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
# SIGNAL POUR CRÉER REVENU PROPRIÉTAIRE
# ============================================================================
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

@receiver(post_save, sender=Reservation)
def envoyer_emails_creation_reservation(sender, instance, created, **kwargs):
    """Envoie un email au client et à l'hôte quand une réservation est créée"""
    if not created:
        return

    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))

        context = {
            'reservation': instance,
            'client': instance.user,
            'hote': instance.bien.owner,
            'bien': instance.bien,
        }

        # Email client
        if instance.user and instance.user.email:
            subject_client = f"Confirmation de votre réservation #{instance.id} - {instance.bien.nom}"
            html_client = render_to_string('reservations/email_reservation_client.html', context)
            text_client = strip_tags(html_client)

            mail_client = EmailMultiAlternatives(
                subject_client, text_client, from_email, [instance.user.email]
            )
            mail_client.attach_alternative(html_client, 'text/html')
            mail_client.send(fail_silently=True)

        # Email hôte
        if instance.bien.owner and instance.bien.owner.email:
            subject_hote = f"Nouvelle réservation pour votre bien « {instance.bien.nom} » (#{instance.id})"
            html_hote = render_to_string('reservations/email_reservation_hote.html', context)
            text_hote = strip_tags(html_hote)

            mail_hote = EmailMultiAlternatives(
                subject_hote, text_hote, from_email, [instance.bien.owner.email]
            )
            mail_hote.attach_alternative(html_hote, 'text/html')
            mail_hote.send(fail_silently=True)

    except Exception as e:
        # Évite de casser la création de réservation en cas d'erreur email
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur envoi email réservation #{instance.id}: {e}")

class BienImage(models.Model):
    bien = models.ForeignKey('reservation.Bien', related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=bien_image_upload_to)  # Chaque image ira dans "biens/<slug ou id>/"