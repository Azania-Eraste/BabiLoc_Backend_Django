from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.utils import timezone

class Message(models.Model):
    """
    Modèle pour représenter un message entre utilisateurs
    """
    expediteur = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='messages_envoyes',
        verbose_name="Expéditeur"
    )
    destinataire = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='messages_recus',
        verbose_name="Destinataire"
    )
    objet = models.CharField(
        max_length=200, 
        verbose_name="Objet",
        blank=True
    )
    contenu = models.TextField(verbose_name="Contenu")
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date d'envoi"
    )
    lu = models.BooleanField(
        default=False,
        verbose_name="Message lu"
    )
    archive_expediteur = models.BooleanField(
        default=False,
        verbose_name="Archivé par l'expéditeur"
    )
    archive_destinataire = models.BooleanField(
        default=False,
        verbose_name="Archivé par le destinataire"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.expediteur.username} → {self.destinataire.username}: {self.objet[:50]}"

    def marquer_comme_lu(self):
        """Marque le message comme lu"""
        self.lu = True
        self.save()

class Conversation(models.Model):
    """
    Modèle pour regrouper les messages en conversations
    """
    participants = models.ManyToManyField(
        User,
        related_name='conversations',
        verbose_name="Participants"
    )
    dernier_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Dernier message"
    )
    cree_le = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de création"
    )
    mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière mise à jour"
    )

    class Meta:
        ordering = ['-mise_a_jour']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        participants = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation: {participants}"

    def get_messages(self):
        """Retourne tous les messages de la conversation"""
        participants = list(self.participants.all())
        if len(participants) == 2:
            return Message.objects.filter(
                expediteur__in=participants,
                destinataire__in=participants
            ).order_by('timestamp')
        return Message.objects.none()

    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Récupère ou crée une conversation entre deux utilisateurs"""
        conversation = cls.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        ).first()
        
        if not conversation:
            conversation = cls.objects.create()
            conversation.participants.add(user1, user2)
        
        return conversation