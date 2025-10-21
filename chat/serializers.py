from rest_framework import serializers
from .models import ChatRoom, ChatMessage, SignalementChat
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


class SignalementChatSerializer(serializers.ModelSerializer):
    reporter_id = serializers.IntegerField(source='reporter.id', read_only=True)
    chat_room_supabase_id = serializers.CharField(write_only=True, required=True)
    chat_room = ChatRoomSerializer(read_only=True)

    class Meta:
        model = SignalementChat
        fields = [
            'id', 'chat_room', 'chat_room_supabase_id', 'reporter', 'reporter_id',
            'message', 'created_at', 'handled', 'handled_by', 'handled_at'
        ]
        read_only_fields = ['id', 'chat_room', 'reporter', 'reporter_id', 'created_at', 'handled', 'handled_by', 'handled_at']

    def validate(self, attrs):
        supabase_id = attrs.get('chat_room_supabase_id')
        if not supabase_id:
            raise serializers.ValidationError({'chat_room_supabase_id': 'Ce champ est requis.'})
        try:
            chat_room = ChatRoom.objects.get(supabase_id=supabase_id)
        except ChatRoom.DoesNotExist:
            raise serializers.ValidationError({'chat_room_supabase_id': 'Salon de chat introuvable.'})
        attrs['chat_room'] = chat_room
        return attrs

    def create(self, validated_data):
        # chat_room was injected in validate
        chat_room = validated_data.pop('chat_room')
        message = validated_data.get('message', '')
        reporter = self.context.get('reporter')
        return SignalementChat.objects.create(
            chat_room=chat_room,
            reporter=reporter if reporter and not isinstance(reporter, dict) else None,
            message=message,
        )