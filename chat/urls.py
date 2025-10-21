from django.urls import path
from .views import (
    UserChatRoomsView,
    ChatMessagesView,
    SendMessageView,
    ChatByReservationView,
    MarkMessagesAsReadView,
    ChatNotificationsView,
    RealtimeStatusView,
    TestRealtimeMessageView,
    SignalementCreateView,
    SignalementsListView,
    SignalementDetailView,
)

app_name = 'chat'

urlpatterns = [
    # Récupérer toutes les conversations de l'utilisateur
    path('rooms/', UserChatRoomsView.as_view(), name='user-chat-rooms'),
    
    # Messages d'une conversation
    path('rooms/<str:chat_room_id>/messages/', ChatMessagesView.as_view(), name='chat-messages'),
    
    # Envoyer un message
    path('rooms/<str:chat_room_id>/send/', SendMessageView.as_view(), name='send-message'),
    
    # Marquer comme lu
    path('rooms/<str:chat_room_id>/mark-read/', MarkMessagesAsReadView.as_view(), name='mark-messages-read'),
    
    # Chat par réservation
    path('reservations/<int:reservation_id>/chat/', ChatByReservationView.as_view(), name='chat-by-reservation'),
    
    # Notifications
    path('notifications/', ChatNotificationsView.as_view(), name='chat-notifications'),
    
    # ✅ NOUVEAUX ENDPOINTS TEMPS RÉEL
    path('realtime/status/', RealtimeStatusView.as_view(), name='realtime-status'),
    path('test-realtime/', TestRealtimeMessageView.as_view(), name='test-realtime'),
    # Signalement d'une room de chat
    path('signalement/', SignalementCreateView.as_view(), name='chat-signalement'),
    # Admin HTML pages for reports
    path('signalements/', SignalementsListView.as_view(), name='chat-signalements-list'),
    path('signalements/<int:pk>/', SignalementDetailView.as_view(), name='chat-signalement-detail'),
]