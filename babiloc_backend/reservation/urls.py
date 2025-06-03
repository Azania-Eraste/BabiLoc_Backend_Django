from django.urls import path
from .viewserializer import (
    CreateReservationView,
    MesReservationsView,
    AllReservationsView,
    ReservationDetailView,
    reservation_stats
)

urlpatterns = [
    # Endpoints principaux
    path('api/reservations/', CreateReservationView.as_view(), name='create-reservation'),
    path('api/mes-reservations/', MesReservationsView.as_view(), name='mes-reservations'),
    path('api/all-reservations/', AllReservationsView.as_view(), name='all-reservations'),
    
    # Détails et mise à jour
    path('api/reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),
    
    # Statistiques
    path('api/admin/reservation-stats/', reservation_stats, name='reservation-stats'),
]