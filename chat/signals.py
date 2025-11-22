from django.db.models.signals import post_save
from django.dispatch import receiver
from reservation.models import Reservation
from .models import ChatRoom
from .supabase_service import chat_supabase_service
import logging
# --- ▼▼▼ AJOUTS ▼▼▼ ---
from notifications.services import send_push_to_user, create_in_app_notification
# --- ▲▲▲ FIN DES AJOUTS ▲▲▲ ---

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Reservation)
def create_chat_room_on_reservation(sender, instance, created, **kwargs):
    """
    Crée automatiquement un chat ET envoie des notifications
    quand une réservation est créée
    """
    if created:
        try:
            # ... (votre logique de création de chat room) ...
            if hasattr(instance, 'chat_room'):
                logger.info(f"Chat déjà existant pour la réservation {instance.id}")
            else:
                result = chat_supabase_service.create_chat_room(
                    reservation_id=instance.id,
                    user_id=instance.user.id,
                    host_id=instance.bien.owner.id,
                    property_name=instance.bien.nom
                )
                if result['success']:
                    ChatRoom.objects.create(
                        supabase_id=result['supabase_id'],
                        reservation=instance,
                        user=instance.user,
                        host=instance.bien.owner,
                        property_name=instance.bien.nom,
                        status='active'
                    )
                    logger.info(f"Chat créé pour réservation {instance.id}")
                else:
                    logger.error(f"Échec création chat réservation {instance.id}: {result.get('error')}")

            # --- ▼▼▼ LOGIQUE DE NOTIFICATION AJOUTÉE ▼▼▼ ---
            
            # 1. Définir les destinataires et le contenu
            item_owner = instance.bien.owner # Le propriétaire du bien
            renter = instance.user         # Le locataire
            
            message_body = f"{renter.username} a fait une demande pour votre bien '{instance.bien.nom}'."
            link_url = f"/reservations/{instance.id}" # Lien pour le clic In-App

            # 2. Envoyer le PUSH au propriétaire
            send_push_to_user(
                user=item_owner, 
                title="Nouvelle réservation !", 
                body=message_body,
                data={'screen': 'ReservationDetails', 'id': str(instance.id)}
            )
            
            # 3. Créer la notification IN-APP pour le propriétaire
            create_in_app_notification(
                user=item_owner,
                message=message_body,
                type='reservation',
                link=link_url
            )
            # --- ▲▲▲ FIN DES AJOUTS ▲▲▲ ---
                
        except Exception as e:
            logger.error(f"Erreur signal réservation {instance.id}: {str(e)}")