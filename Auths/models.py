from django.db import models
from django.contrib.auth.models import AbstractUser
import random
import string
from django.utils import timezone
from datetime import timedelta
from Auths.utils import document_upload_to
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Create your models here.

def upload_path_cni(instance, filename):
    return f"documents/cni/{instance.user.id}/{filename}"

def upload_path_permis(instance, filename):
    return f"documents/permis/{instance.user.id}/{filename}"


class CustomUser(AbstractUser):
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
    
    # ✅ S'assurer que l'email est unique
    email = models.EmailField(
        verbose_name='email address',
        unique=True,  # Forcer l'unicité
        blank=False   # Email obligatoire
    )
    
    number = models.TextField(null=True)
    birthdate = models.DateField(null=True)
    carte_identite = models.FileField(upload_to=upload_path_cni, null=True, blank=True)
    permis_conduire = models.FileField(upload_to=upload_path_permis, null=True, blank=True)
    est_verifie = models.BooleanField(default=False)  # Pour marquer si les documents sont vérifiés manuellement
    is_vendor = models.BooleanField(default=False)
    photo_profil = models.ImageField(upload_to='photos_profil/', null=True, blank=True)
    image_banniere = models.ImageField(upload_to='bannieres/', null=True, blank=True)
    
    # Nouveaux champs pour OTP
    otp_code = models.CharField(max_length=4, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    
    # Système de parrainage
    code_parrainage = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Code de parrainage"
    )
    parrain = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='filleuls',
        verbose_name="Parrain"
    )
    recompense_parrainage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Récompense de parrainage"
    )
    nb_parrainages = models.IntegerField(
        default=0,
        verbose_name="Nombre de parrainages"
    )
    date_parrainage = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de parrainage"
    )
    parrainage_actif = models.BooleanField(
        default=True,
        verbose_name="Parrainage actif"
    )
    points_parrainage = models.IntegerField(
        default=0,
        verbose_name="Points de parrainage"
    )
    
    # ==================== SYSTÈME DE PARRAINAGE ====================
    
    # Code de parrainage unique pour chaque utilisateur
    code_parrainage = models.CharField(
        max_length=10, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Code unique pour parrainer d'autres utilisateurs"
    )
    
    # Référence vers le parrain (celui qui a parrainé cet utilisateur)
    parrain = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='filleuls',
        help_text="Utilisateur qui a parrainé ce compte"
    )
    
    # Date de parrainage
    date_parrainage = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date à laquelle cet utilisateur a été parrainé"
    )
    
    # Statut du parrainage
    parrainage_actif = models.BooleanField(
        default=True,
        help_text="Indique si le parrainage est encore actif"
    )
    
    # Récompenses gagnées via le parrainage
    points_parrainage = models.PositiveIntegerField(
        default=0,
        help_text="Points accumulés grâce au parrainage"
    )
    
    # ==================== MÉTHODES DE PARRAINAGE ====================
    
    def generate_code_parrainage(self):
        """Génère un code de parrainage unique"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not CustomUser.objects.filter(code_parrainage=code).exists():
                self.code_parrainage = code
                self.save()
                return code
    
    def save(self, *args, **kwargs):
        # Générer automatiquement un code de parrainage si pas présent
        if not self.code_parrainage:
            self.generate_code_parrainage()
        super().save(*args, **kwargs)
    
    def parrainer(self, filleul):
        """Parrainer un utilisateur"""
        if filleul.parrain is None:
            filleul.parrain = self
            filleul.date_parrainage = timezone.now()
            filleul.save()
            
            # Incrémenter le nombre de parrainages
            self.nb_parrainages += 1
            self.save()
            
            # Créer un historique de parrainage
            HistoriqueParrainage.objects.create(
                parrain=self,
                filleul=filleul,
                type_action='parrainage',
                description=f"{self.username} a parrainé {filleul.username}"
            )
            
            return True
        return False
    
    def get_filleuls(self):
        """Récupère tous les filleuls de cet utilisateur"""
        return self.filleuls.all()
    
    def get_recompenses_parrainage(self):
        """Calcule les récompenses totales de parrainage"""
        # Récompense de base par filleul
        recompense_base = self.nb_parrainages * 10000  # 10,000 F par filleul
        
        # Bonus selon le nombre de filleuls
        if self.nb_parrainages >= 10:
            bonus = 50000  # 50,000 F bonus pour 10+ filleuls
        elif self.nb_parrainages >= 5:
            bonus = 20000  # 20,000 F bonus pour 5+ filleuls
        else:
            bonus = 0
        
        return recompense_base + bonus
    
    def get_nombre_filleuls(self):
        """Retourne le nombre de filleuls"""
        return self.filleuls.count()
    
    def get_revenus_parrainage(self):
        """Retourne les revenus du parrainage"""
        # Calculer les revenus basés sur les historiques de parrainage
        from django.db.models import Sum
        total_revenus = self.historiques_parrainage.aggregate(
            total=Sum('montant_recompense')
        )['total'] or 0
        return total_revenus
    
    def get_filleuls_actifs(self):
        """Retourne les filleuls avec parrainage actif"""
        return self.filleuls.filter(parrainage_actif=True)
    
    def get_revenus_parrainage(self):
        """Calcule les revenus générés par le parrainage"""
        return self.historiques_parrainage.aggregate(
            total=models.Sum('montant_recompense')
        )['total'] or 0
    
    def save(self, *args, **kwargs):
        # Générer automatiquement un code de parrainage si pas présent
        if not self.code_parrainage:
            self.generate_code_parrainage()
        super().save(*args, **kwargs)

    def generate_otp(self):
        """Génère un code OTP à 4 chiffres"""
        self.otp_code = str(random.randint(1000, 9999))
        self.otp_created_at = timezone.now()
        self.otp_verified = False
        self.save()
        return self.otp_code
    
    def is_otp_valid(self):
        """Vérifie si l'OTP est encore valide (2 minutes)"""
        if not self.otp_created_at:
            return False
        expiry_time = self.otp_created_at + timedelta(minutes=2)
        return timezone.now() <= expiry_time
    
    def verify_otp(self, otp_code):
        """Vérifie le code OTP"""
        # Convertir les deux codes en string pour éviter les problèmes de type
        if str(self.otp_code) == str(otp_code) and self.is_otp_valid():
            self.otp_verified = True
            self.is_active = True
            self.otp_code = None  # Nettoyer le code après utilisation
            self.otp_created_at = None
            self.save()
            return True
        return False

class HistoriqueParrainage(models.Model):
    """Historique des actions de parrainage"""
    
    TYPE_ACTION_CHOICES = [
        ('parrainage', 'Parrainage'),
        ('recompense', 'Récompense'),
        ('bonus', 'Bonus'),
        ('utilisation_code', 'Utilisation de code promo'),
    ]
    
    STATUT_RECOMPENSE_CHOICES = [
        ('en_attente', 'En attente'),
        ('versee', 'Versée'),
        ('annulee', 'Annulée'),
    ]
    
    parrain = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='historiques_parrainage',
        verbose_name="Parrain"
    )
    filleul = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='historique_filleul',
        null=True,
        blank=True,
        verbose_name="Filleul"
    )
    type_action = models.CharField(
        max_length=20,
        choices=TYPE_ACTION_CHOICES,
        verbose_name="Type d'action"
    )
    montant_recompense = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant récompense"
    )
    points_recompense = models.IntegerField(
        default=0,
        verbose_name="Points récompense"
    )
    description = models.TextField(verbose_name="Description")
    statut_recompense = models.CharField(
        max_length=20,
        choices=STATUT_RECOMPENSE_CHOICES,
        default='en_attente',
        verbose_name="Statut récompense"
    )
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date action")
    date_recompense = models.DateTimeField(null=True, blank=True, verbose_name="Date récompense")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    
    class Meta:
        verbose_name = "Historique de parrainage"
        verbose_name_plural = "Historiques de parrainage"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.parrain.username} - {self.get_type_action_display()}"
    
    def get_type_action_display(self):
        return dict(self.TYPE_ACTION_CHOICES).get(self.type_action, self.type_action)
    
    def get_statut_recompense_display(self):
        return dict(self.STATUT_RECOMPENSE_CHOICES).get(self.statut_recompense, self.statut_recompense)


class CodePromoParrainage(models.Model):
    """Codes promo générés par le système de parrainage"""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code promo"
    )
    parrain = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='codes_promo_parrainage',
        verbose_name="Parrain"
    )
    utilisateur = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='codes_promo_crees',
        verbose_name="Utilisateur créateur",
        null=True,
        blank=True
    )
    pourcentage_reduction = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        verbose_name="Pourcentage de réduction"
    )
    reduction_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        verbose_name="Réduction (%)"
    )
    montant_reduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant réduction fixe"
    )
    montant_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50000.00,
        verbose_name="Montant minimum"
    )
    nombre_utilisations_max = models.IntegerField(
        default=1,
        verbose_name="Nombre d'utilisations max"
    )
    nombre_utilisations = models.IntegerField(
        default=0,
        verbose_name="Nombre d'utilisations"
    )
    date_expiration = models.DateTimeField(verbose_name="Date d'expiration")
    utilise = models.BooleanField(default=False, verbose_name="Utilisé")
    est_actif = models.BooleanField(default=True, verbose_name="Actif")
    date_utilisation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'utilisation"
    )
    utilise_par = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='codes_promo_utilises',
        null=True,
        blank=True,
        verbose_name="Utilisé par"
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date création")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    
    class Meta:
        verbose_name = "Code promo parrainage"
        verbose_name_plural = "Codes promo parrainage"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.parrain.username if self.parrain else self.utilisateur.username}"
    
    def is_valid(self):
        """Vérifie si le code promo est encore valide"""
        return (self.est_actif and 
                not self.utilise and 
                timezone.now() < self.date_expiration and
                self.nombre_utilisations < self.nombre_utilisations_max)
    
    def utiliser(self, utilisateur):
        """Utilise le code promo"""
        if self.is_valid():
            self.nombre_utilisations += 1
            if self.nombre_utilisations >= self.nombre_utilisations_max:
                self.utilise = True
                self.date_utilisation = timezone.now()
                self.utilise_par = utilisateur
            self.save()
            
            # Créer un historique
            HistoriqueParrainage.objects.create(
                parrain=self.parrain or self.utilisateur,
                filleul=utilisateur,
                type_action='utilisation_code',
                description=f"Code promo {self.code} utilisé par {utilisateur.username}"
            )
            
            return True
        return False


# ==================== SIGNAUX POUR AUTOMATISER LES RÉCOMPENSES ====================

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def parrainage_inscription(sender, instance, created, **kwargs):
    """Déclenche les récompenses lors de l'inscription d'un nouvel utilisateur"""
    if created and instance.parrain:
        # Créer un historique de parrainage
        HistoriqueParrainage.objects.create(
            parrain=instance.parrain,
            filleul=instance,
            type_action='inscription',
            montant_recompense=5000,  # 5000 FCFA bonus
            points_recompense=100,
            description=f"Bonus d'inscription pour le parrainage de {instance.username}"
        )

@receiver(post_save, sender='reservation.Reservation')
def parrainage_reservation(sender, instance, created, **kwargs):
    """Déclenche les récompenses lors des réservations"""
    if created and instance.user.parrain:
        # Vérifier si c'est la première réservation
        premiere_reservation = not sender.objects.filter(
            user=instance.user
        ).exclude(id=instance.id).exists()
        
        if premiere_reservation:
            HistoriqueParrainage.objects.create(
                parrain=instance.user.parrain,
                filleul=instance.user,
                type_action='premiere_reservation',
                montant_recompense=10000,  # 10000 FCFA bonus
                points_recompense=200,
                description=f"Bonus de première réservation de {instance.user.username}",
                reservation=instance
            )
    
    # Bonus pour réservation complétée
    if instance.status == 'completed' and instance.user.parrain:
        # Calculer le bonus (5% du montant de la réservation)
        bonus_montant = instance.prix_total * 0.05
        
        HistoriqueParrainage.objects.create(
            parrain=instance.user.parrain,
            filleul=instance.user,
            type_action='reservation_complete',
            montant_recompense=bonus_montant,
            points_recompense=50,
            description=f"Bonus de réservation complétée (5% de {instance.prix_total})",
            reservation=instance
        )


class DocumentUtilisateur(models.Model):
    """Documents de vérification des utilisateurs"""
    TYPE_DOCUMENT_CHOICES = [
        ('carte_identite', 'Carte d\'identité'),
        ('permis_conduire', 'Permis de conduire'),
        ('passeport', 'Passeport'),
        ('attestation_travail', 'Attestation de travail'),
        ('justificatif_domicile', 'Justificatif de domicile'),
        ('rccm', 'Document RCCM'),  # ✅ Ajouter pour les entreprises
        ('autre', 'Autre document'),
    ]
    
    STATUT_VERIFICATION_CHOICES = [
        ('en_attente', 'En attente de vérification'),
        ('approuve', 'Approuvé'),
        ('refuse', 'Refusé'),
        ('expire', 'Expiré'),
    ]
    
    utilisateur = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='documents_verification'
    )
    nom = models.CharField(max_length=255, verbose_name="Nom du document")
    type_document = models.CharField(
        max_length=50, 
        choices=TYPE_DOCUMENT_CHOICES,
        verbose_name="Type de document"
    )
    
    # Soit un fichier soit une image
    fichier = models.FileField(
        upload_to=document_upload_to,
        blank=True,
        null=True,
        verbose_name="Fichier document",
        # validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'webp'])]
    )
    image = models.ImageField(
        upload_to=document_upload_to,
        blank=True,
        null=True,
        verbose_name="Image du document",
        # validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    statut_verification = models.CharField(
        max_length=20,
        choices=STATUT_VERIFICATION_CHOICES,
        default='en_attente',
        verbose_name="Statut de vérification"
    )
    
    date_expiration = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Date d'expiration"
    )
    
    commentaire_moderateur = models.TextField(
        blank=True,
        null=True,
        verbose_name="Commentaire du modérateur"
    )
    
    date_upload = models.DateTimeField(auto_now_add=True)
    date_verification = models.DateTimeField(null=True, blank=True)
    moderateur = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_moderes'
    )
    
    # Nouveaux champs pour les entreprises
    structure_type = models.CharField(
        max_length=50,
        choices=[
            ('particulier', 'Particulier / Individuel'),
            ('agence', 'Agence de location'),
            ('societe', 'Société'),
        ],
        default='particulier',
        verbose_name="Type de structure"
    )
    
    agence_nom = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nom de l'agence/société"
    )
    
    agence_adresse = models.TextField(
        blank=True,
        null=True,
        verbose_name="Adresse complète"
    )
    
    representant_telephone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Téléphone représentant légal"
    )

    class Meta:
        verbose_name = "Document utilisateur"
        verbose_name_plural = "Documents utilisateur"
        unique_together = ('utilisateur', 'type_document')  # Un seul document par type
    
    def clean(self):
        """Validation personnalisée"""
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
        """Retourne le type de fichier"""
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
    
    def is_expired(self):
        """Vérifie si le document est expiré"""
        if self.date_expiration:
            from django.utils import timezone
            return timezone.now().date() > self.date_expiration
        return False
    
    def __str__(self):
        return f"{self.get_type_document_display()} - {self.utilisateur.username}"


class AccountDeletionLog(models.Model):
    user_id = models.IntegerField()
    email = models.EmailField(null=True, blank=True)
    username = models.CharField(max_length=150, blank=True)
    is_vendor = models.BooleanField(default=False)
    reason = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reservations_count = models.IntegerField(default=0)
    favoris_count = models.IntegerField(default=0)
    avis_count = models.IntegerField(default=0)
    hard_delete = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(
        CustomUser, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='deletions_performed'
    )

    class Meta:
        ordering = ['-deleted_at']
        verbose_name = "Suppression de compte"
        verbose_name_plural = "Suppressions de compte"

    def __str__(self):
        return f"Suppression user#{self.user_id} - {self.deleted_at:%Y-%m-%d %H:%M}"