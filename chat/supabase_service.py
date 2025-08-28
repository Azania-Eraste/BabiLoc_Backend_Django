from supabase import create_client
from django.conf import settings
import logging
from datetime import datetime
from .models import ChatRoom

logger = logging.getLogger(__name__)

class ChatSupabaseService:
    def __init__(self):
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    def create_chat_room(self, reservation_id, user_id, host_id, property_name):
        """
        Crée une room de chat dans Supabase et localement
        """
        try:
            # Données pour Supabase
            chat_room_data = {
                'reservation_id': reservation_id,
                'user_id': user_id,
                'host_id': host_id,
                'property_name': property_name,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'last_message_at': datetime.utcnow().isoformat()
            }
            
            # Créer dans Supabase
            result = self.supabase.table('chat_rooms').insert(chat_room_data).execute()
            
            if result.data:
                supabase_room = result.data[0]
                logger.info(f"Chat room créée dans Supabase: {supabase_room['id']}")
                
                # Envoyer message de bienvenue
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
        """
        Envoie un message de bienvenue automatique
        """
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
        Envoie un message dans Supabase
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
                return {
                    'success': True,
                    'message_id': result.data[0]['id'],
                    'data': result.data[0]
                }
            return {'success': False, 'error': 'Message non envoyé'}
            
        except Exception as e:
            logger.error(f"Erreur envoi message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_chat_rooms_for_user(self, user_id):
        """
        Récupère les rooms de chat d'un utilisateur
        """
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
        """
        Récupère les messages d'une room
        """
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
        """
        Marque tous les messages non lus d'une conversation comme lus pour un utilisateur
        """
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
        """
        Récupère le nombre de messages non lus pour un utilisateur
        """
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