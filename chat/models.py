from django.db import models
from django.contrib.auth import get_user_model
from reservation.models import Reservation

User = get_user_model()

class ChatRoom(models.Model):
    """
    Modèle local pour synchroniser avec Supabase
    """
    supabase_id = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True,
        verbose_name="ID Supabase"
    )
    reservation = models.OneToOneField(
        Reservation, 
        on_delete=models.CASCADE,
        related_name='chat_room',
        verbose_name="Réservation"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_user',
        verbose_name="Utilisateur"
    )
    host = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_host',
        verbose_name="Hôte"
    )
    property_name = models.CharField(
        max_length=255,
        verbose_name="Nom du bien"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Actif'),
            ('closed', 'Fermé'),
            ('archived', 'Archivé')
        ],
        default='active',
        verbose_name="Statut"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    last_message_at = models.DateTimeField(auto_now=True, verbose_name="Dernier message")
    
    class Meta:
        verbose_name = "Salon de chat"
        verbose_name_plural = "Salons de chat"
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"Chat - {self.property_name} ({self.user.username} ↔ {self.host.username})"
    
    @property
    def participants(self):
        """Retourne la liste des participants"""
        return [self.user, self.host]
    
    def is_participant(self, user):
        """Vérifie si l'utilisateur est participant au chat"""
        return user in self.participants

class ChatMessage(models.Model):
    """
    Modèle local pour les messages (optionnel, pour cache local)
    """
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Salon de chat"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Expéditeur"
    )
    message = models.TextField(verbose_name="Message")
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Texte'),
            ('image', 'Image'),
            ('file', 'Fichier'),
            ('system', 'Système')
        ],
        default='text',
        verbose_name="Type de message"
    )
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    
    class Meta:
        verbose_name = "Message de chat"
        verbose_name_plural = "Messages de chat"
        ordering = ['created_at']
    
    def __str__(self):
        sender_name = self.sender.username if self.sender else "Système"
        return f"{sender_name}: {self.message[:50]}..."


class SignalementChat(models.Model):
    """Signalement d'une room de chat par un utilisateur.

    Permet aux administrateurs de recevoir une alerte et d'intervenir.
    """
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='signalements',
        verbose_name="Salon de chat"
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Utilisateur ayant signalé"
    )
    message = models.TextField(verbose_name="Message du signalement", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    handled = models.BooleanField(default=False, verbose_name="Traité")
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_chat_reports',
        verbose_name="Traité par"
    )
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name="Traité le")

    class Meta:
        verbose_name = "Signalement de chat"
        verbose_name_plural = "Signalements de chat"
        ordering = ['-created_at']

    def __str__(self):
        return f"Signalement #{self.id} - room:{self.chat_room.supabase_id or self.chat_room.id} reporter:{self.reporter.username if self.reporter else 'anon'}"
