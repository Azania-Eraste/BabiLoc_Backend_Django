from django.urls import path
from .views import SoldeHoteView, HistoriquePaiementsView
from .viewserializer import (
    CreateReservationView,
    MesReservationsView,
    AllReservationsView,
    ReservationDetailView,
    reservation_stats,
    BienListCreateView,
    BienDetailView,
    MediaCreateView

)

urlpatterns = [
    # Endpoints principaux
    path('api/reservations/', CreateReservationView.as_view(), name='create-reservation'),
    path('api/mes-reservations/', MesReservationsView.as_view(), name='mes-reservations'),
    path('api/all-reservations/', AllReservationsView.as_view(), name='all-reservations'),
    
    # Détails et mise à jour
    path('api/reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),

    #Biens
    path('api/biens/', BienListCreateView.as_view(), name='biens-list-create'),
    path('api/biens/<int:pk>/', BienDetailView.as_view(), name='biens-detail'),
    path('medias/', MediaCreateView.as_view(), name='media-create'),
    
    #Hote
    path('hote/solde/', SoldeHoteView.as_view(), name='hote-solde'),

    #historique
    path('api/historique-paiements/', HistoriquePaiementsView.as_view(), name='historique-paiements'),

    # Statistiques
    path('api/admin/reservation-stats/', reservation_stats, name='reservation-stats'),
]