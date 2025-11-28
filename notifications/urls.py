from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FCMDeviceViewSet, NotificationFeedView, UnreadCountView, MarkAllAsReadView # 👈 AJOUTS

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
    
    # --- ▼▼▼ NOUVELLES ROUTES AJOUTÉES ▼▼▼ ---
    path('feed/', NotificationFeedView.as_view(), name='notification-feed'),
    path('unread-count/', UnreadCountView.as_view(), name='notification-unread-count'),
    path('mark-as-read/', MarkAllAsReadView.as_view(), name='notification-mark-as-read'),
]