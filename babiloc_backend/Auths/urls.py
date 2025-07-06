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
]
