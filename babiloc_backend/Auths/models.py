from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    number = models.TextField()
    birthdate = models.DateField()
    is_vendor = models.BooleanField(default=False)