from django.db.models.signals import post_save
from django.dispatch import receiver
from reservation.models import Reservation
from .models import ChatRoom
from .supabase_service import chat_supabase_service
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Reservation)
def create_chat_room_on_reservation(sender, instance, created, **kwargs):
    """
    Crée automatiquement un chat quand une réservation est créée
    """
    if created:
        try:
            # Vérifier qu'il n'y a pas déjà un chat pour cette réservation
            if hasattr(instance, 'chat_room'):
                logger.info(f"Chat déjà existant pour la réservation {instance.id}")
                return
            
            # Créer le chat dans Supabase
            result = chat_supabase_service.create_chat_room(
                reservation_id=instance.id,
                user_id=instance.user.id,
                host_id=instance.bien.owner.id,
                property_name=instance.bien.nom
            )
            
            if result['success']:
                # Créer l'enregistrement local
                chat_room = ChatRoom.objects.create(
                    supabase_id=result['supabase_id'],
                    reservation=instance,
                    user=instance.user,
                    host=instance.bien.owner,
                    property_name=instance.bien.nom,
                    status='active'
                )
                
                logger.info(f"Chat créé pour réservation {instance.id}: {chat_room.id}")
                
            else:
                logger.error(f"Échec création chat réservation {instance.id}: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Erreur création chat réservation {instance.id}: {str(e)}")