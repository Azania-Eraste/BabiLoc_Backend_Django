from supabase import create_client
from django.conf import settings
import logging
from datetime import datetime
from .models import ChatRoom
# --- ▼▼▼ AJOUTS ▼▼▼ ---
from notifications.services import send_push_to_user, create_in_app_notification
# --- ▲▲▲ FIN DES AJOUTS ▲▲▲ ---

logger = logging.getLogger(__name__)

class ChatSupabaseService:
    def __init__(self):
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    def create_chat_room(self, reservation_id, user_id, host_id, property_name):
        # ... (code inchangé) ...
        try:
            chat_room_data = {
                'reservation_id': reservation_id,
                'user_id': user_id,
                'host_id': host_id,
                'property_name': property_name,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'last_message_at': datetime.utcnow().isoformat()
            }
            result = self.supabase.table('chat_rooms').insert(chat_room_data).execute()
            if result.data:
                supabase_room = result.data[0]
                logger.info(f"Chat room créée dans Supabase: {supabase_room['id']}")
                self.send_welcome_message(supabase_room['id'], property_name)
                return {
                    'success': True,
                    'supabase_id': supabase_room['id'],
                    'data': supabase_room
                }
            else:
                logger.error("Aucune donnée retournée de Supabase")
                return {'success': False, 'error': 'Aucune donnée retournée'}
        except Exception as e:
            logger.error(f"Erreur création chat Supabase: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_welcome_message(self, chat_room_id, property_name):
        # ... (code inchangé) ...
        try:
            welcome_message = {
                'chat_room_id': chat_room_id,
                'sender_id': None,  # Message système
                'message': f"🎉 Félicitations ! Votre réservation pour '{property_name}' a été créée. Vous pouvez maintenant discuter avec votre hôte.",
                'message_type': 'system',
                'created_at': datetime.utcnow().isoformat(),
                'is_read': False
            }
            result = self.supabase.table('chat_messages').insert(welcome_message).execute()
            if result.data:
                logger.info(f"Message de bienvenue envoyé: {chat_room_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur envoi message bienvenue: {str(e)}")
            return False
    
    def send_message(self, chat_room_id, sender_id, message, message_type='text'):
        """
        Envoie un message dans Supabase ET déclenche les notifications
        """
        try:
            message_data = {
                'chat_room_id': chat_room_id,
                'sender_id': sender_id,
                'message': message,
                'message_type': message_type,
                'created_at': datetime.utcnow().isoformat(),
                'is_read': False
            }
            
            result = self.supabase.table('chat_messages').insert(message_data).execute()
            
            # Mettre à jour le timestamp de la room
            self.supabase.table('chat_rooms').update({
                'last_message_at': datetime.utcnow().isoformat()
            }).eq('id', chat_room_id).execute()
            
            if result.data:
                # --- ▼▼▼ LOGIQUE DE NOTIFICATION AJOUTÉE ▼▼▼ ---
                self.notify_recipient_on_new_message(chat_room_id, sender_id, message)
                # --- ▲▲▲ FIN DES AJOUTS ▲▲▲ ---
                return {
                    'success': True,
                    'message_id': result.data[0]['id'],
                    'data': result.data[0]
                }
            return {'success': False, 'error': 'Message non envoyé'}
            
        except Exception as e:
            logger.error(f"Erreur envoi message: {str(e)}")
            return {'success': False, 'error': str(e)}

    # --- ▼▼▼ NOUVELLE FONCTION AJOUTÉE ▼▼▼ ---
    def notify_recipient_on_new_message(self, chat_room_id, sender_id, message_content):
        try:
            # 1. Trouver le salon de chat local pour identifier les utilisateurs
            room = ChatRoom.objects.get(supabase_id=chat_room_id)
            
            # 2. Identifier l'expéditeur et le destinataire
            # Note: sender_id de Supabase est un UUID, nous devons le comparer aux IDs Django
            if str(room.user.id) == str(sender_id):
                sender = room.user
                recipient = room.host
            elif str(room.host.id) == str(sender_id):
                sender = room.host
                recipient = room.user
            else:
                logger.warning(f"Impossible de trouver l'expéditeur {sender_id} dans le salon {chat_room_id}")
                return

            # 3. Définir le contenu
            title = f"Nouveau message de {sender.username}"
            body = message_content
            link_url = f"/chat/{room.id}"
            
            # 4. Envoyer le PUSH au destinataire
            send_push_to_user(
                user=recipient, 
                title=title, 
                body=body,
                data={'screen': 'ChatRoom', 'id': str(room.id)}
            )
            
            # 5. Créer la notification IN-APP pour le destinataire
            create_in_app_notification(
                user=recipient,
                message=f"{sender.username}: {body[:50]}...", # Tronquer le message
                type='message',
                link=link_url
            )
            
        except ChatRoom.DoesNotExist:
            logger.error(f"ChatRoom local non trouvé pour supabase_id {chat_room_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la notification de nouveau message: {e}")
            
    # ... (le reste de votre fichier supabase_service.py) ...
    def get_chat_rooms_for_user(self, user_id):
        # ... (code inchangé) ...
        try:
            result = self.supabase.table('chat_rooms').select('*').or_(
                f'user_id.eq.{user_id},host_id.eq.{user_id}'
            ).order('last_message_at', desc=True).execute()
            
            return {
                'success': True,
                'data': result.data
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération rooms: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_chat_messages(self, chat_room_id, limit=50):
        # ... (code inchangé) ...
        try:
            result = self.supabase.table('chat_messages').select('*').eq(
                'chat_room_id', chat_room_id
            ).order('created_at', desc=True).limit(limit).execute()
            
            return {
                'success': True,
                'data': list(reversed(result.data))  # Ordre chronologique
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération messages: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def mark_messages_as_read(self, chat_room_id, user_id):
        # ... (code inchangé) ...
        try:
            result = self.supabase.table('chat_messages').update({
                'is_read': True
            }).eq('chat_room_id', chat_room_id).neq('sender_id', user_id).eq('is_read', False).execute()
            
            if result.data:
                logger.info(f"Messages marqués comme lus: {len(result.data)} messages")
                return {
                    'success': True,
                    'messages_updated': len(result.data)
                }
            return {
                'success': True,
                'messages_updated': 0
            }
            
        except Exception as e:
            logger.error(f"Erreur marquage messages lus: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_unread_count(self, user_id):
        # ... (code inchangé) ...
        try:
            # Récupérer toutes les rooms de l'utilisateur
            user_rooms = self.get_chat_rooms_for_user(user_id)
            if not user_rooms['success']:
                return {'success': False, 'error': 'Erreur récupération rooms'}
            
            total_unread = 0
            room_unread = {}
            
            for room in user_rooms['data']:
                # Compter les messages non lus dans chaque room (pas envoyés par l'utilisateur)
                result = self.supabase.table('chat_messages').select('id').eq(
                    'chat_room_id', room['id']
                ).neq('sender_id', user_id).eq('is_read', False).execute()
                
                unread_count = len(result.data) if result.data else 0
                room_unread[room['id']] = unread_count
                total_unread += unread_count
            
            return {
                'success': True,
                'total_unread': total_unread,
                'room_unread': room_unread
            }
            
        except Exception as e:
            logger.error(f"Erreur comptage messages non lus: {str(e)}")
            return {'success': False, 'error': str(e)}

# Instance globale
chat_supabase_service = ChatSupabaseService()