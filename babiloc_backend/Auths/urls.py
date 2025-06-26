from django.urls import path
from django.urls import path
from .views import RegisterView, ActivateAccountView, ForgotPasswordView, ResetPasswordConfirmView, MeView, MyTokenObtainPairView, ProfileUpdateView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/<uidb64>/<token>/', ActivateAccountView.as_view(), name='activate'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordConfirmView.as_view(), name='reset-password'),
    path('me/', MeView.as_view(), name='me'),
    path('update/', ProfileUpdateView.as_view(), name='Udpate-user'),
]
