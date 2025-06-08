from django.urls import path
from . import views

app_name = 'messagerie'

urlpatterns = [
    path('', views.boite_reception, name='boite_reception'),
    path('envoyes/', views.messages_envoyes, name='messages_envoyes'),
    path('nouveau/', views.nouveau_message, name='nouveau_message'),
    path('nouveau/<int:destinataire_id>/', views.nouveau_message, name='nouveau_message_destinataire'),
    path('message/<int:message_id>/', views.lire_message, name='lire_message'),
    path('conversations/', views.conversations, name='conversations'),
    path('conversation/<int:conversation_id>/', views.voir_conversation, name='voir_conversation'),
]