from rest_framework import serializers
from .models import FCMDevice, AppNotification # 👈 AJOUT

class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        # Champs attendus de l'app mobile
        fields = ['device_token', 'platform']
        extra_kwargs = {
            'device_token': {'required': True},
            'platform': {'required': True},
        }

# --- ▼▼▼ NOUVEAU SERIALIZER AJOUTÉ ▼▼▼ ---
class AppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppNotification
        fields = ['id', 'message', 'is_read', 'timestamp', 'type', 'link']