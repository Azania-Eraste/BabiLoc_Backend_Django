from django.urls import path
from .views import (
    UserChatRoomsView,
    ChatMessagesView,
    SendMessageView,
    ChatByReservationView
)

app_name = 'chat'

urlpatterns = [
    # Récupérer toutes les conversations de l'utilisateur
    path('rooms/', UserChatRoomsView.as_view(), name='user-chat-rooms'),
    
    # Messages d'une conversation
    path('rooms/<str:chat_room_id>/messages/', ChatMessagesView.as_view(), name='chat-messages'),
    
    # Envoyer un message
    path('rooms/<str:chat_room_id>/send/', SendMessageView.as_view(), name='send-message'),
    
    # Chat par réservation
    path('reservations/<int:reservation_id>/', ChatByReservationView.as_view(), name='chat-by-reservation'),
]