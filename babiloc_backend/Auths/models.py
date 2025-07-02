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
        """Vérifie si l'OTP est encore valide (5 minutes)"""
        if not self.otp_created_at:
            return False
        expiry_time = self.otp_created_at + timedelta(minutes=5)
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