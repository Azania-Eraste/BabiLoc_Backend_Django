from django.db import models
from django.conf import settings

class FCMDevice(models.Model):
    # Lier l'appareil à votre CustomUser
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='fcm_devices'
    )
    # Le token FCM (peut être long)
    device_token = models.TextField(unique=True, db_index=True)
    
    # Savoir si c'est iOS ou Android
    PLATFORM_CHOICES = [('ios', 'iOS'), ('android', 'Android')]
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Device for {self.user.username} ({self.platform})"


# --- ▼▼▼ NOUVEAU MODÈLE AJOUTÉ ▼▼▼ ---
class AppNotification(models.Model):
    """
    Modèle pour le "centre de notifications" DANS l'application.
    """
    NOTIFICATION_TYPES = [
        ('reservation', 'Réservation'),
        ('message', 'Message'),
        ('favori', 'Favori'),
        ('autre', 'Autre'),
    ]

    # L'utilisateur qui DOIT recevoir la notification
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='autre')
    link = models.CharField(max_length=255, blank=True, null=True) # Ex: /reservation/123

    class Meta:
        ordering = ['-timestamp'] # Les plus récentes en premier

    def __str__(self):
        return f"Notif pour {self.user.username}: {self.message[:30]}"