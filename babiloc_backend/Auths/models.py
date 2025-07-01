from django.db import models
from django.contrib.auth.models import AbstractUser

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