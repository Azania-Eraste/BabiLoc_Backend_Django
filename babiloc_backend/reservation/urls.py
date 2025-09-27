from django.urls import path, include
from .views import (
    SoldeHoteView, 
    HistoriquePaiementsView,
    CreateReservationView,
    MesReservationsView,
    AllReservationsView,
    ReservationDetailView,
    CreatePaymentView,
    PaymentStatusView,
    CinetPayWebhookView,
    cancel_payment,
    HistoriqueRevenusProprietaireView,  # ✅ Ajouter cette import
    FactureListView,
    FactureDetailView,
    FactureCreateView,
    FactureDownloadView,
    FactureResendEmailView,
    FacturesHoteView,
    # ✅ Nouvelles vues pour la disponibilité
    obtenir_disponibilite_vehicule,
    verifier_disponibilite_periode,
    forcer_mise_a_jour_disponibilite,
    mettre_a_jour_statuts_automatique,
    reservations_bien,  # ✅ Nouvelle vue pour les réservations d'un bien
    confirm_reservation_payment,  # ✅ Nouveau endpoint pour confirmer après paiement
    ChoicesView,  # ✅ Nouvelle vue pour les choices
    cancel_reservation, # Import de la nouvelle vue d'annulation de réservation
)

# ✅ Garder les imports depuis viewserializer.py pour les autres vues
from .viewserializer import (
    reservations_stats,
    historique_statuts_reservations_bien,
    BienListCreateView,
    BienDetailView,
    MesBiensView,
    VerifierDroitAvisView,
    MoyenneAvisProprietaireView,
    AvisRecusProprietaireView,
    MediaCreateView,
    MediaDeleteView,
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
    # ✅ Nouvelles vues pour les avis après réservation
    reservations_sans_avis,
    creer_avis_reservation,
    profil_avis_proprietaire,
    repondre_avis,
    TypeBienListCreateView,
    TypeBienDetailView,
    DocumentCreateView,
    DocumentListView,
    DocumentUpdateView,
    DocumentDeleteView,
    MesReservationsHostView,
    VilleListView
    
)

urlpatterns = [
    # Endpoints principaux
    path('reservations/', CreateReservationView.as_view(), name='create-reservation'),
    path('mes-reservations/', MesReservationsView.as_view(), name='mes-reservations'),
    path('all-reservations/', AllReservationsView.as_view(), name='all-reservations'),
    
    # Détails et mise à jour
    path('reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),
    path('reservations/peut-noter/<int:bien_id>/', VerifierDroitAvisView.as_view(), name='verifier-droit-avis'),
    path('proprietaire/<int:user_id>/moyenne-avis/', MoyenneAvisProprietaireView.as_view(), name='moyenne-avis-proprietaire'),
    path('proprietaire/<int:user_id>/avis-recus/', AvisRecusProprietaireView.as_view(), name='avis-recus-proprietaire'),
    path('reservations/cancel_reservation/', cancel_reservation, name='cancel-reservation'), # Nouvelle route d'annulation

    # Types de bien
    path('types-bien/', TypeBienListCreateView.as_view(), name='types-bien-list-create'),
    path('types-bien/<int:pk>/', TypeBienDetailView.as_view(), name='types-bien-detail'),

    # Biens
    path('biens/', BienListCreateView.as_view(), name='biens-list-create'),
    path('biens/<int:pk>/', BienDetailView.as_view(), name='biens-detail'),
    path('biens/mes-biens/', MesBiensView.as_view(), name='mes-biens'),
    path('medias/', MediaCreateView.as_view(), name='media-create'),
    path('medias/<int:pk>/', MediaDeleteView.as_view(), name='media-delete'),
    
    # Villes
    path('villes/', VilleListView.as_view(), name='villes-list'),

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
    path('Dashboard/mes-reservations/', MesReservationsHostView.as_view(), name='hote-mes-reservations'),

    #historique
    path('Dashboard/historique-paiements/', HistoriquePaiementsView.as_view(), name='historique-paiements'),

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
    path('biens/<int:bien_id>/avis/', statistiques_avis_bien, name='avis-bien'),  # ✅ Nouvelle route
    path('biens/<int:bien_id>/avis/statistiques/', statistiques_avis_bien, name='statistiques-avis-bien'),
    path('mes-avis/', mes_avis, name='mes-avis'),
    path('Dashboard/avis-recus/', avis_recus, name='avis-recus'),
    
    # ✅ Nouvelles routes pour les avis après réservation
    path('reservations/sans-avis/', reservations_sans_avis, name='reservations-sans-avis'),
    path('avis/creer/', creer_avis_reservation, name='creer-avis-reservation'),
    path('Dashboard/profil-avis/', profil_avis_proprietaire, name='profil-avis-proprietaire'),
    path('avis/profil/<int:user_id>/', profil_avis_proprietaire, name='avis-profil-mobile'),
    path('avis/repondre/', repondre_avis, name='repondre-avis'),

    # Paiements CinetPay
    path('payments/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payments/status/', PaymentStatusView.as_view(), name='payment-status'),
    path('payments/cancel/', cancel_payment, name='cancel-payment'),
    
    # Webhooks
    path('webhooks/cinetpay/', CinetPayWebhookView.as_view(), name='cinetpay-webhook'),

    # Documents
    path('documents/create/', DocumentCreateView.as_view(), name='document-create'),
    path('biens/<int:bien_id>/documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:pk>/update/', DocumentUpdateView.as_view(), name='document-update'),
    path('documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document-delete'),

    # Factures
    path('factures/', FactureListView.as_view(), name='factures-list'),
    path('factures/<int:pk>/', FactureDetailView.as_view(), name='facture-detail'),
    path('factures/create/', FactureCreateView.as_view(), name='facture-create'),
    path('factures/<int:pk>/download/', FactureDownloadView.as_view(), name='facture-download'),
    path('factures/<int:pk>/resend-email/', FactureResendEmailView.as_view(), name='facture-resend-email'),
    path('hote/factures/', FacturesHoteView.as_view(), name='factures-hote'),
    
    # ✅ Nouvelles routes pour la disponibilité
    path('biens/<int:bien_id>/disponibilite/', obtenir_disponibilite_vehicule, name='obtenir-disponibilite-vehicule'),
    path('biens/<int:bien_id>/verifier-disponibilite/', verifier_disponibilite_periode, name='verifier-disponibilite-periode'),
    path('biens/<int:bien_id>/forcer-mise-a-jour-disponibilite/', forcer_mise_a_jour_disponibilite, name='forcer-mise-a-jour-disponibilite'),
    path('admin/mettre-a-jour-statuts/', mettre_a_jour_statuts_automatique, name='mettre-a-jour-statuts-automatique'),
    
    # ✅ Nouvelle route pour récupérer les réservations d'un bien
    path('reservations-bien/', reservations_bien, name='reservations-bien'),
    
    # ✅ Endpoint pour confirmer réservation après paiement
    path('confirm-payment/', confirm_reservation_payment, name='confirm-reservation-payment'),
    
    # ✅ Endpoint pour récupérer les choices
    path('choices/', ChoicesView.as_view(), name='choices'),
]