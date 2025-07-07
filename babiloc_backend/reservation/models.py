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
class Bien(models.Model):
    
    nom = models.CharField(max_length=250)  # Ex: "Villa moderne 4 chambres"
    description = models.TextField()  # Description complète du bien
    ville = models.CharField(max_length=100, verbose_name="Ville", default="Abidjan")
    
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

    # Exemple de champ spécifique à un véhicule
    marque = models.CharField(max_length=100, null=True, blank=True)
    modele = models.CharField(max_length=100, null=True, blank=True)
    plaque = models.CharField(max_length=20, null=True, blank=True)
    nb_places = models.IntegerField(null=True, blank=True)

    # Exemple pour une maison
    nb_chambres = models.IntegerField(null=True, blank=True)
    has_piscine = models.BooleanField(null=True, blank=True)

    est_verifie = models.BooleanField(default=False)

    def get_first_image(self):
        """Récupère la première image du bien pour l'affichage en liste"""
        return self.medias.first().image.url if self.medias.exists() else None
    
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
    fichier = models.FileField(upload_to='documents_biens/')
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
    bien = models.ForeignKey(Bien,on_delete=models.CASCADE, related_name='Tarifs_Biens_id')
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
    bien = models.ForeignKey('Bien', on_delete=models.CASCADE, related_name='medias')
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
    
    annonce_id = models.ForeignKey(Bien,on_delete=models.CASCADE, related_name='Reservation_Bien_ids')
    
    frais_service_percent = Decimal("0.15")

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
    def frais_service(self):
        return round(self.prix_total * self.frais_service_percent, 2)

    @property
    def revenu_net_hote(self):
        return round(self.prix_total - self.frais_service, 2)

    def get_tarif_bien(self):
        return self.annonce_id.Tarifs_Biens_id.filter(type_tarif=self.type_tarif).first()
    
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
    montant = models.FloatField()
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    mode = models.ForeignKey(Mode, on_delete=models.CASCADE, related_name="ModePaiement", null=True, blank=True)  # ✅ Rendre optionnel
    
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