from django.db import models
from django.contrib.auth.models import AbstractUser
import random
from django.utils import timezone
from datetime import timedelta

# Create your models here.

def upload_path_cni(instance, filename):
    return f"documents/cni/{instance.user.id}/{filename}"

def upload_path_permis(instance, filename):
    return f"documents/permis/{instance.user.id}/{filename}"


class CustomUser(AbstractUser):
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

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
        if self.otp_code == otp_code and self.is_otp_valid():
            self.otp_verified = True
            self.is_active = True
            self.otp_code = None  # Nettoyer le code après utilisation
            self.otp_created_at = None
            self.save()
            return True
        return False

class DocumentUtilisateur(models.Model):
    """Documents de vérification des utilisateurs"""
    
    TYPE_DOCUMENT_CHOICES = [
        ('carte_identite', 'Carte d\'identité'),
        ('permis_conduire', 'Permis de conduire'),
        ('passeport', 'Passeport'),
        ('attestation_travail', 'Attestation de travail'),
        ('justificatif_domicile', 'Justificatif de domicile'),
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
        upload_to='documents_utilisateurs/fichiers/', 
        blank=True, 
        null=True,
        verbose_name="Fichier document"
    )
    image = models.ImageField(
        upload_to='documents_utilisateurs/images/', 
        blank=True, 
        null=True,
        verbose_name="Image du document"
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