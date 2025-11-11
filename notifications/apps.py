import firebase_admin
from firebase_admin import credentials
from django.apps import AppConfig
from django.conf import settings
import os

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # Chemin vers votre clé (elle doit être à la racine, à côté de manage.py)
        cred_path = os.path.join(settings.BASE_DIR, 
                                 'babiloc-notifications-firebase-adminsdk-fbsvc-ef74ca20e4.json')
        
        # Éviter de ré-initialiser l'app (problème de rechargement)
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin SDK initialisé avec succès.")
            except FileNotFoundError:
                print(f"ERREUR: Fichier de clé Firebase non trouvé à {cred_path}")
            except Exception as e:
                print(f"Erreur lors de l'initialisation de Firebase: {e}")