from rest_framework import serializers
from .models import FCMDevice

class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        # Champs attendus de l'app mobile
        fields = ['device_token', 'platform']
        extra_kwargs = {
            'device_token': {'required': True},
            'platform': {'required': True},
        }