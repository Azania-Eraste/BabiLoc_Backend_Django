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