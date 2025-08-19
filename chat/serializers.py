from rest_framework import serializers
from .models import ChatRoom, ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializer pour les salons de chat
    """
    user_name = serializers.CharField(source='user.username', read_only=True)
    host_name = serializers.CharField(source='host.username', read_only=True)
    reservation_id = serializers.IntegerField(source='reservation.id', read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'supabase_id', 'reservation_id', 'user', 'host',
            'user_name', 'host_name', 'property_name', 'status',
            'created_at', 'last_message_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_message_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer pour les messages de chat
    """
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat_room', 'sender', 'sender_name', 'message',
            'message_type', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class SendMessageSerializer(serializers.Serializer):
    """
    Serializer pour envoyer un message
    """
    message = serializers.CharField(max_length=1000)
    message_type = serializers.ChoiceField(
        choices=[('text', 'Texte'), ('image', 'Image'), ('file', 'Fichier')],
        default='text'
    )