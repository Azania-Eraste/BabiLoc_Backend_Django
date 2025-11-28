from firebase_admin import messaging
from .models import FCMDevice, AppNotification # Importe les DEUX modèles
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

def send_push_to_user(user: User, title: str, body: str, data: dict = None):
    """
    Système A: Envoie une notification PUSH (FCM) à tous les appareils 
    actifs d'un utilisateur.
    'data' est un dict pour des infos sup (ex: {'reservationId': '123'})
    """
    # 1. Trouver les tokens de l'utilisateur
    devices = user.fcm_devices.filter(is_active=True)
    tokens = [device.device_token for device in devices]

    if not tokens:
        print(f"Pas de tokens PUSH actifs trouvés pour {user.username}.")
        return

    # S'assurer que toutes les données sont des strings
    string_data = {str(k): str(v) for k, v in data.items()} if data else {}

    # 2. Préparer le message universel
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=string_data, 
        tokens=tokens,
        
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', content_available=True)
            )
        ),
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(sound='default')
        )
    )

    # 3. Envoyer
    try:
        response = messaging.send_multicast(message)
        print(f"Notifs PUSH envoyées à {user.username}: {response.success_count} succès.")
        
        # 4. Nettoyage (important)
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    error_code = resp.exception.code
                    if error_code in ('messaging/registration-token-not-registered', 
                                      'messaging/invalid-registration-token'):
                        failed_tokens.append(tokens[idx])
            
            if failed_tokens:
                print(f"Désactivation de {len(failed_tokens)} tokens PUSH invalides.")
                FCMDevice.objects.filter(device_token__in=failed_tokens).update(is_active=False)

    except Exception as e:
        print(f"Erreur majeure PUSH: {e}")


def create_in_app_notification(user: User, message: str, type: str, link: str = None):
    """
    Système B: Crée une notification DANS LA BASE DE DONNÉES (pour le flux).
    """
    try:
        AppNotification.objects.create(
            user=user,
            message=message,
            type=type,
            link=link
        )
        print(f"Notification IN-APP créée pour {user.username}")
    except Exception as e:
        print(f"Erreur lors de la création de la notif In-App: {e}")