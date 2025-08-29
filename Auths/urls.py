from django.urls import path
from .views import (
    RegisterView, ForgotPasswordView, ResetPasswordConfirmView, 
    MeView, MyTokenObtainPairView, ProfileUpdateView, welcome_view,
    VerifyOTPView, ResendOTPView, ActivateAccountView,
    DocumentUtilisateurCreateView,
    MesDocumentsView,
    DocumentUtilisateurUpdateView,
    DocumentUtilisateurDeleteView,
    DocumentsModerationView,
    DocumentModerationView,
    DebugUserStatusView,
    GetUserByIdView,
    MonParrainageView, MesFilleulsView, HistoriqueParrainageView,
    generer_code_promo, statistiques_parrainage, verifier_code_parrainage,
    demander_retrait, valider_code_promo,
    DevenirVendorView,  # ✅ Vérifier que c'est bien importé
    vendor_admin_dashboard, vendor_requests_list, vendor_action  # Ajout des vues pour l'admin vendor
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordConfirmView.as_view(), name='reset-password'),
    path('me/', MeView.as_view(), name='me'),
    path('update/', ProfileUpdateView.as_view(), name='update-user'),
    path('welcome/', welcome_view, name='welcome'),
    path('user/<int:user_id>/', GetUserByIdView.as_view(), name='get-user-by-id'),

        # Informations de parrainage
    path('parrainage/mon-parrainage/', MonParrainageView.as_view(), name='mon-parrainage'),
    path('parrainage/mes-filleuls/', MesFilleulsView.as_view(), name='mes-filleuls'),
    path('parrainage/historique/', HistoriqueParrainageView.as_view(), name='historique-parrainage'),
    path('parrainage/statistiques/', statistiques_parrainage, name='statistiques-parrainage'),
    
    # Codes de parrainage
    path('parrainage/verifier-code/', verifier_code_parrainage, name='verifier-code-parrainage'),
    
    # Codes promo
    path('parrainage/generer-code-promo/', generer_code_promo, name='generer-code-promo'),
    path('parrainage/valider-code-promo/', valider_code_promo, name='valider-code-promo'),
    
    # Retraits
    path('parrainage/demander-retrait/', demander_retrait, name='demander-retrait'),


    # Ancien endpoint pour compatibilité
    path('activate/<uidb64>/<token>/', ActivateAccountView.as_view(), name='activate'),

    # Documents utilisateur
    path('documents/upload/', DocumentUtilisateurCreateView.as_view(), name='document-upload'),
    path('documents/mes-documents/', MesDocumentsView.as_view(), name='mes-documents'),
    path('documents/<int:pk>/update/', DocumentUtilisateurUpdateView.as_view(), name='document-update'),
    path('documents/<int:pk>/delete/', DocumentUtilisateurDeleteView.as_view(), name='document-delete'),
    
    # Modération
    path('admin/documents/moderation/', DocumentsModerationView.as_view(), name='documents-moderation'),
    path('admin/documents/<int:pk>/moderer/', DocumentModerationView.as_view(), name='document-moderer'),

    # Debug
    path('debug-user-status/', DebugUserStatusView.as_view(), name='debug-user-status'),  # Temporaire

    # Vendor
    path('devenir-vendor/', DevenirVendorView.as_view(), name='devenir-vendor'),

    # Vendor Admin Interface
    path('vendor/vendor-dashboard/', vendor_admin_dashboard, name='vendor_dashboard'),
    path('vendor/vendor-requests/', vendor_requests_list, name='vendor_requests_list'),
    path('vendor/vendor-action/', vendor_action, name='vendor_action'),
]
