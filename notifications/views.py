from rest_framework import viewsets, status, generics, views # 👈 AJOUTS
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import FCMDevice, AppNotification # 👈 AJOUT
from .serializers import FCMDeviceSerializer, AppNotificationSerializer # 👈 AJOUT

class FCMDeviceViewSet(viewsets.GenericViewSet):
    """
    Endpoint pour enregistrer (POST) ou désactiver (DELETE) 
    un appareil pour les notifications push.
    """
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer
    permission_classes = [IsAuthenticated] # Seuls les utilisateurs connectés

    def get_queryset(self):
        # Un utilisateur ne gère que ses propres appareils
        return FCMDevice.objects.filter(user=self.request.user)

    def create(self, request):
        """
        Gère POST /api/notifications/register-device/
        Enregistre ou met à jour un token d'appareil.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_token = serializer.validated_data['device_token']
        
        # Utilise update_or_create pour gérer les ré-enregistrements
        # Si le token existe, il met à jour l'utilisateur associé
        device, created = FCMDevice.objects.update_or_create(
            device_token=device_token,
            defaults={
                'user': request.user,
                'platform': serializer.validated_data['platform'],
                'is_active': True
            }
        )
        
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)
        
    def destroy(self, request, *args, **kwargs):
        """
        Gère DELETE /api/notifications/register-device/
        Utilisé lors de la déconnexion de l'utilisateur.
        L'app mobile doit envoyer son token dans le body.
        """
        token = request.data.get('device_token')
        if not token:
            return Response({"detail": "device_token manquant."},
                            status=status.HTTP_400_BAD_REQUEST)
                            
        try:
            # On ne supprime que parmi les tokens de l'utilisateur connecté
            device = self.get_queryset().get(device_token=token)
            device.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FCMDevice.DoesNotExist:
            return Response({"detail": "Appareil non trouvé pour cet utilisateur."},
                            status=status.HTTP_404_NOT_FOUND)

# --- ▼▼▼ NOUVELLES VUES API AJOUTÉES ▼▼▼ ---

class NotificationFeedView(generics.ListAPIView):
    """
    API pour GET /api/notifications/feed/
    Renvoie la liste des notifications In-App pour l'utilisateur connecté.
    """
    serializer_class = AppNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    # ▼▼▼ AJOUTEZ CETTE LIGNE POUR DÉSACTIVER LA PAGINATION ▼▼▼
    pagination_class = None 
    # ▲▲▲ FIN DE L'AJOUT ▲▲▲

    def get_queryset(self):
        # Renvoie seulement les notifications pour l'utilisateur
        return AppNotification.objects.filter(user=self.request.user)

class UnreadCountView(views.APIView):
    """
    API pour GET /api/notifications/unread-count/
    Renvoie le nombre de notifications non lues.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        count = AppNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count}, status=status.HTTP_200_OK)

class MarkAllAsReadView(views.APIView):
    """
    API pour POST /api/notifications/mark-as-read/
    Marque toutes les notifications de l'utilisateur comme lues.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        AppNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'Toutes les notifications ont été marquées comme lues'}, status=status.HTTP_200_OK)