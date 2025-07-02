from django.urls import path, include
from .views import (
    SoldeHoteView, 
    HistoriquePaiementsView,
    CreateReservationView,
    MesReservationsView,
    AllReservationsView,
    ReservationDetailView,  # ✅ Maintenant disponible dans views.py
    CreatePaymentView,
    PaymentStatusView,
    CinetPayWebhookView,
    cancel_payment,
)

# ✅ Garder les imports depuis viewserializer.py pour les autres vues
from .viewserializer import (
    reservations_stats,
    historique_statuts_reservations_bien,
    BienListCreateView,
    BienDetailView,
    MediaCreateView,
    AjouterFavoriView,
    MesFavorisView,
    RetirerFavoriView,
    toggle_favori,
    likes_de_mon_bien,
    TarifCreateView,
    TarifDeleteView,
    TarifUpdateView,
    AvisListCreateView,
    AvisDetailView,
    ReponseProprietaireView,
    statistiques_avis_bien,
    mes_avis,
    avis_recus,
)

urlpatterns = [
    # Endpoints principaux
    path('reservations/', CreateReservationView.as_view(), name='create-reservation'),
    path('mes-reservations/', MesReservationsView.as_view(), name='mes-reservations'),
    path('all-reservations/', AllReservationsView.as_view(), name='all-reservations'),
    
    # Détails et mise à jour
    path('reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),

    # Biens
    path('biens/', BienListCreateView.as_view(), name='biens-list-create'),
    path('biens/<int:pk>/', BienDetailView.as_view(), name='biens-detail'),
    path('medias/', MediaCreateView.as_view(), name='media-create'),
    
    #Tarifs
    path('tarifs/create/', TarifCreateView.as_view(), name='tarif-create'),
    path('tarifs/<int:pk>/update/', TarifUpdateView.as_view(), name='tarif-update'),
    path('tarifs/<int:pk>/delete/', TarifDeleteView.as_view(), name='tarif-delete'),

    # Favoris
    path('favoris/', AjouterFavoriView.as_view(), name='ajouter-favori'),
    path('mes-favoris/', MesFavorisView.as_view(), name='mes-favoris'),
    path('favoris/<int:pk>/', RetirerFavoriView.as_view(), name='retirer-favori'),
    path('favoris/toggle/', toggle_favori, name='toggle-favori'),
    
    
    #Hote
    path('Dashboard/solde/', SoldeHoteView.as_view(), name='hote-solde'),

    #historique
    path('Dashboard/historique-paiements/', HistoriquePaiementsView.as_view(), name='historique-paiements'),

    # Statistiques
    path('admin/reservation-stats/', reservations_stats, name='reservation-stats'),
    path('Dashboard/biens/<int:bien_id>/reservations/historiques-statuts/', historique_statuts_reservations_bien, name='historiques_statuts_reservations_bien'),
    path('Dashboard/biens/<int:bien_id>/likes', likes_de_mon_bien, name='likes_de_mon_bien'),

    # Avis
    path('avis/', AvisListCreateView.as_view(), name='avis-list-create'),
    path('avis/<int:pk>/', AvisDetailView.as_view(), name='avis-detail'),
    path('avis/<int:pk>/repondre/', ReponseProprietaireView.as_view(), name='avis-repondre'),
    path('biens/<int:bien_id>/avis/statistiques/', statistiques_avis_bien, name='statistiques-avis-bien'),
    path('mes-avis/', mes_avis, name='mes-avis'),
    path('avis-recus/', avis_recus, name='avis-recus'),

    # Paiements CinetPay
    path('payments/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payments/status/', PaymentStatusView.as_view(), name='payment-status'),
    path('payments/cancel/', cancel_payment, name='cancel-payment'),
    
    # Webhooks
    path('webhooks/cinetpay/', CinetPayWebhookView.as_view(), name='cinetpay-webhook'),
]