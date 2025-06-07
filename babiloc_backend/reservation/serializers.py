from rest_framework import serializers
from .models import Reservation, Bien, Media
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les informations utilisateur"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'number', 'date_joined']
        read_only_fields = ['id', 'username', 'date_joined']

class ReservationSerializer(serializers.ModelSerializer):
    """Serializer complet pour les réservations"""
    
    user = UserSerializer(read_only=True)
    duree_jours = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'annonce_id', 'date_debut', 'date_fin',
            'status', 'status_display', 'prix_total', 'message',
            'duree_jours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class BienSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bien
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ReservationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une réservation"""
    
    class Meta:
        model = Reservation
        fields = ['annonce_id', 'date_debut', 'date_fin', 'prix_total', 'message']
    
    def validate(self, data):
        """Validation personnalisée"""
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        
        # Vérifier que les dates sont dans le futur
        now = timezone.now()
        if date_debut and date_debut <= now:
            raise serializers.ValidationError({
                'date_debut': 'La date de début doit être dans le futur.'
            })
        
        # Vérifier que date_fin > date_debut
        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError({
                'date_fin': 'La date de fin doit être après la date de début.'
            })
        
        return data

class ReservationUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour le statut d'une réservation"""
    
    class Meta:
        model = Reservation
        fields = ['status', 'message']
    
    def validate_status(self, value):
        """Validation du changement de statut"""
        instance = self.instance
        if instance and instance.status == 'completed':
            raise serializers.ValidationError(
                "Une réservation terminée ne peut pas être modifiée."
            )
        return value

class ReservationListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes"""
    
    user_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'user_info', 'annonce_id', 'date_debut', 'date_fin',
            'status', 'status_display', 'prix_total', 'created_at'
        ]
    
    def get_user_info(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': f"{obj.user.first_name} {obj.user.last_name}".strip(),
            'number': getattr(obj.user, 'number', '')
        }
    
class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'image']