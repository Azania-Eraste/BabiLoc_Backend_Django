from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FCMDeviceViewSet

# Crée un routeur
router = DefaultRouter()

# Enregistre notre ViewSet.
# 'register-device' sera le préfixe de l'URL.
router.register(r'register-device', FCMDeviceViewSet, basename='device')

# Les URLs de l'API sont maintenant déterminées par le routeur.
# - POST /api/notifications/register-device/ (pour 'create')
# - DELETE /api/notifications/register-device/ (pour 'destroy')
urlpatterns = [
    path('', include(router.urls)),
]