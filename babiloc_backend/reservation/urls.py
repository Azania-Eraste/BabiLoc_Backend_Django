from django.urls import path
from .views import SoldeHoteView, HistoriquePaiementsView
from .viewserializer import (
    CreateReservationView,
    MesReservationsView,
    AllReservationsView,
    ReservationDetailView,
    reservations_stats,
    historique_statuts_reservations_bien,
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
    path('Dashboard/solde/', SoldeHoteView.as_view(), name='hote-solde'),

    #historique
    path('Dashboard/historique-paiements/', HistoriquePaiementsView.as_view(), name='historique-paiements'),

    # Statistiques
    path('api/admin/reservation-stats/', reservations_stats, name='reservation-stats'),
    path('Dashboard/biens/<int:bien_id>/reservations/historiques-statuts/', historique_statuts_reservations_bien, name='historiques_statuts_reservations_bien'),

]