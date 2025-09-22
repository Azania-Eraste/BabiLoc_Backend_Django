from django.shortcuts import render
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .supabase_service import chat_supabase_service
from .models import ChatRoom
from reservation.models import Reservation
from django.shortcuts import get_object_or_404
from .serializers import ChatRoomSerializer
from django.utils import timezone

class UserChatRoomsView(APIView):
    """
    Récupérer toutes les conversations de l'utilisateur
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer toutes les conversations de l'utilisateur connecté",
        responses={
            200: openapi.Response(
                description="Liste des conversations",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY, 
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'property_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'last_message_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'other_user': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'role': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    ),
                                    'reservation_details': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'property_name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                                            'check_in': openapi.Schema(type=openapi.TYPE_STRING),
                                            'check_out': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                }
                            )
                        )
                    }
                )
            ),
            401: "Non authentifié"
        },
        tags=['Chat']
    )
    def get(self, request):
        # Récupérer depuis Supabase
        result = chat_supabase_service.get_chat_rooms_for_user(request.user.id)
        
        if result['success']:
            # Enrichir avec les données locales
            for room in result['data']:
                try:
                    # Récupérer les détails de la réservation
                    reservation = Reservation.objects.select_related('bien', 'user').get(
                        id=room['reservation_id']
                    )
                    
                    room['reservation_details'] = {
                        'id': reservation.id,
                        'property_name': reservation.bien.nom,
                        'guest_name': f"{reservation.user.first_name} {reservation.user.last_name}".strip() or reservation.user.username,
                        'host_name': f"{reservation.bien.owner.first_name} {reservation.bien.owner.last_name}".strip() or reservation.bien.owner.username,
                        'status': reservation.status,
                        'check_in': reservation.date_debut.isoformat(),
                        'check_out': reservation.date_fin.isoformat(),
                        'property_image': request.build_absolute_uri(reservation.bien.media.first().image.url) if reservation.bien.media.exists() else None
                    }
                    
                    # Déterminer qui est l'autre participant
                    if room['user_id'] == request.user.id:
                        room['other_user'] = {
                            'id': room['host_id'],
                            'name': room['reservation_details']['host_name'],
                            'role': 'host'
                        }
                    else:
                        room['other_user'] = {
                            'id': room['user_id'],
                            'name': room['reservation_details']['guest_name'],
                            'role': 'guest'
                        }
                        
                except Reservation.DoesNotExist:
                    room['reservation_details'] = None
                    room['other_user'] = None
        
            return Response(result, status=status.HTTP_200_OK)
        
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

class ChatMessagesView(APIView):
    """
    Récupérer les messages d'une conversation
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer les messages d'une conversation",
        manual_parameters=[
            openapi.Parameter(
                'chat_room_id',
                openapi.IN_PATH,
                description="ID de la room de chat Supabase",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Nombre de messages à récupérer (défaut: 50)",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: openapi.Response(
                description="Messages récupérés avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'chat_room_id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'sender_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                                    'message_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'is_read': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'sender_info': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'username': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                }
                            )
                        )
                    }
                )
            ),
            400: "Erreur dans la requête",
            401: "Non authentifié",
            403: "Accès refusé"
        },
        tags=['Chat']
    )
    def get(self, request, chat_room_id):
        # Vérifier l'accès à cette conversation
        user_rooms = chat_supabase_service.get_chat_rooms_for_user(request.user.id)
        if not user_rooms['success']:
            return Response({'error': 'Erreur lors de la vérification des permissions'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si l'utilisateur a accès à cette room
        user_has_access = any(room['id'] == chat_room_id for room in user_rooms['data'])
        if not user_has_access:
            return Response({
                'error': 'Accès refusé à cette conversation',
                'debug': {
                    'user_id': request.user.id,
                    'requested_room_id': chat_room_id,
                    'available_room_ids': [room['id'] for room in user_rooms['data']]
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        limit = int(request.query_params.get('limit', 50))
        result = chat_supabase_service.get_chat_messages(chat_room_id, limit)
        
        if result['success']:
            # Enrichir les messages avec les infos utilisateur
            for message in result['data']:
                if message['sender_id']:
                    try:
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        sender = User.objects.get(id=message['sender_id'])
                        message['sender_info'] = {
                            'id': sender.id,
                            'name': f"{sender.first_name} {sender.last_name}".strip() or sender.username,
                            'username': sender.username
                        }
                    except:
                        message['sender_info'] = None
                else:
                    message['sender_info'] = {'name': 'Système', 'username': 'system'}
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

class SendMessageView(APIView):
    """
    Envoyer un message dans une conversation
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Envoyer un message dans une conversation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['message'],
            properties={
                'message': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Contenu du message',
                    example="Bonjour, j'ai une question concernant ma réservation."
                ),
                'message_type': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    default='text', 
                    enum=['text', 'image', 'file'],
                    description='Type de message'
                )
            }
        ),
        responses={
            201: openapi.Response(
                description="Message envoyé avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING),
                                'chat_room_id': openapi.Schema(type=openapi.TYPE_STRING),
                                'sender_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                                'message_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_read': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                            }
                        )
                    }
                )
            ),
            400: "Erreur dans la requête",
            401: "Non authentifié",
            403: "Accès refusé"
        },
        tags=['Chat']
    )
    def post(self, request, chat_room_id):
        # Vérifier l'accès
        user_rooms = chat_supabase_service.get_chat_rooms_for_user(request.user.id)
        if not user_rooms['success']:
            return Response({'error': 'Erreur lors de la vérification des permissions'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        user_has_access = any(room['id'] == chat_room_id for room in user_rooms['data'])
        if not user_has_access:
            return Response({
                'error': 'Accès refusé à cette conversation',
                'debug': {
                    'user_id': request.user.id,
                    'requested_room_id': chat_room_id,
                    'available_room_ids': [room['id'] for room in user_rooms['data']]
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        message = request.data.get('message')
        message_type = request.data.get('message_type', 'text')
        
        if not message:
            return Response({'error': 'Le message ne peut pas être vide'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        result = chat_supabase_service.send_message(
            chat_room_id=chat_room_id,
            sender_id=request.user.id,
            message=message,
            message_type=message_type
        )
        
        return Response(result, status=status.HTTP_201_CREATED if result['success'] else status.HTTP_400_BAD_REQUEST)

class ChatByReservationView(APIView):
    """
    Récupérer le chat associé à une réservation
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer le chat pour une réservation spécifique",
        responses={
            200: openapi.Response(
                description="Chat trouvé",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'chat_room_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'local_chat_id': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            404: "Chat non trouvé",
            401: "Non authentifié",
            403: "Accès refusé"
        },
        tags=['Chat']
    )
    def get(self, request, reservation_id):
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        # Vérifier l'accès
        if request.user != reservation.user and request.user != reservation.bien.owner:
            return Response({'error': 'Accès refusé à cette réservation'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            chat_room = ChatRoom.objects.get(reservation=reservation)
            return Response({
                'success': True,
                'chat_room_id': chat_room.supabase_id,
                'reservation_id': reservation.id,
                'local_chat_id': chat_room.id
            }, status=status.HTTP_200_OK)
        except ChatRoom.DoesNotExist:
            return Response({'error': 'Aucun chat associé à cette réservation'}, 
                           status=status.HTTP_404_NOT_FOUND)

class ChatRealtimeTestView(APIView):
    """
    Test de la connexion temps réel Supabase
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Tester la connexion temps réel avec Supabase",
        responses={
            200: "Connexion temps réel OK",
            400: "Erreur de connexion"
        },
        tags=['Chat', 'Test']
    )
    def get(self, request):
        try:
            # Test simple de la connexion
            result = chat_supabase_service.supabase.table('chat_rooms').select('id').limit(1).execute()
            
            return Response({
                'success': True,
                'message': 'Connexion Supabase OK',
                'realtime_enabled': True,
                'user_id': request.user.id,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class ChatNotificationsView(APIView):
    """
    Récupérer les notifications de chat (messages non lus)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer le nombre de messages non lus",
        responses={
            200: openapi.Response(
                description="Notifications récupérées",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'total_unread': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'room_unread': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Nombre de messages non lus par room"
                        )
                    }
                )
            ),
            401: "Non authentifié"
        },
        tags=['Chat']
    )
    def get(self, request):
        result = chat_supabase_service.get_unread_count(request.user.id)
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

class MarkMessagesAsReadView(APIView):
    """
    Marquer les messages comme lus
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Marquer tous les messages d'une conversation comme lus",
        responses={
            200: openapi.Response(
                description="Messages marqués comme lus",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'messages_updated': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            403: "Accès refusé",
            404: "Conversation non trouvée"
        },
        tags=['Chat']
    )
    def post(self, request, chat_room_id):
        # Vérifier l'accès
        user_rooms = chat_supabase_service.get_chat_rooms_for_user(request.user.id)
        if not user_rooms['success']:
            return Response({'error': 'Erreur lors de la vérification des permissions'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        user_has_access = any(room['id'] == chat_room_id for room in user_rooms['data'])
        if not user_has_access:
            return Response({'error': 'Accès refusé à cette conversation'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Marquer comme lus dans Supabase
        result = chat_supabase_service.mark_messages_as_read(chat_room_id, request.user.id)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

class RealtimeStatusView(APIView):
    """
    Vérifier le statut du temps réel et des connexions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Vérifier le statut du temps réel Supabase",
        responses={
            200: openapi.Response(
                description="Statut du temps réel",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'supabase_connected': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'realtime_enabled': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                        'test_results': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Erreur de connexion"
        },
        tags=['Chat', 'Realtime']
    )
    def get(self, request):
        try:
            # Test 1: Connexion Supabase de base
            supabase_test = chat_supabase_service.supabase.table('chat_rooms').select('id').limit(1).execute()
            supabase_connected = True
            
            # Test 2: Vérifier les tables nécessaires
            tables_test = {}
            tables_to_check = ['chat_rooms', 'chat_messages']
            
            for table in tables_to_check:
                try:
                    result = chat_supabase_service.supabase.table(table).select('*').limit(1).execute()
                    tables_test[table] = {
                        'exists': True,
                        'count': len(result.data) if result.data else 0
                    }
                except Exception as e:
                    tables_test[table] = {
                        'exists': False,
                        'error': str(e)
                    }
            
            # Test 3: Vérifier les rooms de l'utilisateur
            user_rooms = chat_supabase_service.get_chat_rooms_for_user(request.user.id)
            
            return Response({
                'supabase_connected': supabase_connected,
                'realtime_enabled': True,  # Supabase realtime est activé côté serveur
                'user_id': request.user.id,
                'timestamp': timezone.now().isoformat(),
                'test_results': {
                    'tables': tables_test,
                    'user_rooms': {
                        'success': user_rooms['success'],
                        'count': len(user_rooms['data']) if user_rooms['success'] else 0,
                        'rooms': user_rooms['data'] if user_rooms['success'] else []
                    }
                },
                'instructions': {
                    'frontend': 'Pour le temps réel côté client, utilisez les WebSockets Supabase',
                    'javascript_example': 'supabase.channel("chat").on("postgres_changes", {...}).subscribe()',
                    'flutter_example': 'supabase.channel("chat").onPostgresChanges(...).subscribe()'
                }
            })
            
        except Exception as e:
            return Response({
                'supabase_connected': False,
                'realtime_enabled': False,
                'error': str(e),
                'user_id': request.user.id,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)

class TestRealtimeMessageView(APIView):
    """
    Envoyer un message de test pour vérifier le temps réel
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Envoyer un message de test pour vérifier le temps réel",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'chat_room_id': openapi.Schema(type=openapi.TYPE_STRING, description='ID de la room de chat'),
                'test_message': openapi.Schema(type=openapi.TYPE_STRING, default='Test temps réel')
            }
        ),
        responses={
            201: "Message de test envoyé",
            400: "Erreur"
        },
        tags=['Chat', 'Realtime', 'Test']
    )
    def post(self, request):
        chat_room_id = request.data.get('chat_room_id')
        test_message = request.data.get('test_message', f'🔄 Test temps réel - {timezone.now().strftime("%H:%M:%S")}')
        
        if not chat_room_id:
            return Response({'error': 'chat_room_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier l'accès
        user_rooms = chat_supabase_service.get_chat_rooms_for_user(request.user.id)
        if not user_rooms['success']:
            return Response({'error': 'Erreur vérification permissions'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_has_access = any(room['id'] == chat_room_id for room in user_rooms['data'])
        if not user_has_access:
            return Response({'error': 'Accès refusé à cette conversation'}, status=status.HTTP_403_FORBIDDEN)
        
        # Envoyer le message de test
        result = chat_supabase_service.send_message(
            chat_room_id=chat_room_id,
            sender_id=request.user.id,
            message=test_message,
            message_type='test'
        )
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Message de test envoyé ! Vérifiez votre client temps réel.',
                'data': result['data'],
                'instructions': {
                    'next_step': 'Ouvrez votre application client et vérifiez si le message apparaît automatiquement',
                    'debug': 'Si le message n\'apparaît pas, vérifiez la configuration WebSocket côté client'
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
