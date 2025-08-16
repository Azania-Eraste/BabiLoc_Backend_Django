from django.urls import path, include
from .views import (
    SoldeHoteView, 
    ReservationDetailView,
    HistoriqueRevenusProprietaireView,
)

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
    TarifLookupView,
    AvisListCreateView,
    AvisDetailView,
    ReponseProprietaireView,
    statistiques_avis_bien,
    mes_avis,
    avis_recus,
    TypeBienListCreateView,
    TypeBienDetailView,
    DocumentCreateView,
    DocumentListView,
    DocumentUpdateView,
    DocumentDeleteView,
    MesReservationsHostView,
    VilleListView,
    CreateReservationView,
    MesReservationsView,
    AllReservationsView
)

urlpatterns = [
    # Endpoints principaux
    path('reservations/', CreateReservationView.as_view(), name='create-reservation'),
    path('mes-reservations/', MesReservationsView.as_view(), name='mes-reservations'),
    path('all-reservations/', AllReservationsView.as_view(), name='all-reservations'),
    
    # Détails et mise à jour
    path('reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),

    # Types de bien
    path('types-bien/', TypeBienListCreateView.as_view(), name='types-bien-list-create'),
    path('types-bien/<int:pk>/', TypeBienDetailView.as_view(), name='types-bien-detail'),

    # Biens
    path('biens/', BienListCreateView.as_view(), name='biens-list-create'),
    path('biens/<int:pk>/', BienDetailView.as_view(), name='biens-detail'),
    path('medias/', MediaCreateView.as_view(), name='media-create'),
    
    # Villes
    path('villes/', VilleListView.as_view(), name='villes-list'),

    # Tarifs
    path('tarifs/create/', TarifCreateView.as_view(), name='tarif-create'),
    path('tarifs/<int:pk>/update/', TarifUpdateView.as_view(), name='tarif-update'),
    path('tarifs/<int:pk>/delete/', TarifDeleteView.as_view(), name='tarif-delete'),
    path('biens/<int:bien_id>/tarif/', TarifLookupView.as_view(), name='bien-tarif-lookup'),

    # Favoris
    path('favoris/', AjouterFavoriView.as_view(), name='ajouter-favori'),
    path('mes-favoris/', MesFavorisView.as_view(), name='mes-favoris'),
    path('favoris/<int:pk>/', RetirerFavoriView.as_view(), name='retirer-favori'),
    path('favoris/toggle/', toggle_favori, name='toggle-favori'),
    
    # Hote
    path('Dashboard/solde/', SoldeHoteView.as_view(), name='hote-solde'),
    path('Dashboard/mes-reservations/', MesReservationsHostView.as_view(), name='hote-mes-reservations'),

    # Revenus propriétaire
    path('Dashboard/revenus/', HistoriqueRevenusProprietaireView.as_view(), name='historique-revenus'),

    # Statistiques
    path('Dashboard/reservation-stats/', reservations_stats, name='reservation-stats'),
    path('Dashboard/biens/<int:bien_id>/reservations/historiques-statuts/', historique_statuts_reservations_bien, name='historiques_statuts_reservations_bien'),
    path('Dashboard/biens/<int:bien_id>/likes', likes_de_mon_bien, name='likes_de_mon_bien'),

    # Avis
    path('avis/', AvisListCreateView.as_view(), name='avis-list-create'),
    path('avis/<int:pk>/', AvisDetailView.as_view(), name='avis-detail'),
    path('avis/<int:pk>/repondre/', ReponseProprietaireView.as_view(), name='avis-repondre'),
    path('biens/<int:bien_id>/avis/statistiques/', statistiques_avis_bien, name='statistiques-avis-bien'),
    path('mes-avis/', mes_avis, name='mes-avis'),
    path('Dashboard/avis-recus/', avis_recus, name='avis-recus'),

    # Documents
    path('documents/create/', DocumentCreateView.as_view(), name='document-create'),
    path('biens/<int:bien_id>/documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:pk>/update/', DocumentUpdateView.as_view(), name='document-update'),
    path('documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document-delete'),
]