from .models import CustomUser, DocumentUtilisateur,HistoriqueParrainage,CodePromoParrainage, AccountDeletionLog
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
# Add missing imports
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from .serializers import (
    MyTokenObtainPairSerializer,
    UserSerializer,
    RegisterSerializer,
    DocumentUtilisateurSerializer,
    DocumentModerationSerializer,
    StatistiquesParrainageSerializer,
    FilleulSerializer,
    HistoriqueParrainageSerializer,
    ValidationCodeParrainageSerializer,
    GenerationCodePromoSerializer,
    CodePromotionParrainageSerializer,
    ParrainageSerializer,
    AccountDeletionLogSerializer,  # <- add
)
# Add missing imports
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
import random
import string
from django.db import models  # <- add (utilisé dans AccountDeletionLogListView)
from django.urls import reverse  # utile si besoin plus tard
from django.db import transaction

User = get_user_model()

def welcome_view(request):
    return HttpResponse("<h1>Bienvenue sur Babiloc !</h1><p>Votre plateforme de location.</p>")

class GetUserByIdView(APIView):
    """
    Récupérer les infos d'un utilisateur à partir de son id (pas l'utilisateur connecté)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    
    @swagger_auto_schema(
        operation_description="Connexion avec adresse email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="Adresse email",
                    example="yohannvessime@gmail.com"
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Mot de passe",
                    example="votre_mot_de_passe"
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="Token JWT et infos utilisateur",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_vendor': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'est_verifie': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Erreur de validation",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'requires_otp': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            401: "Identifiants invalides"
        },
        tags=['Authentification']
    )
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur de connexion: {str(e)}")

            email = request.data.get('email')
            print(f"Email: {email}")  # Debugging line
            if email:
                try:
                    user = CustomUser.objects.get(email=email)
                    if not user.is_active:
                        return Response({
                            'error': 'Compte non activé. Veuillez utiliser le code OTP reçu par email.',
                            'user_id': user.id,
                            'requires_activation': True
                        }, status=400)
                except CustomUser.DoesNotExist:
                    pass
            
            return Response({
                'error': 'Identifiants invalides.'
            }, status=401)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Demander un code OTP pour réinitialiser le mot de passe",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="Adresse email de l'utilisateur",
                    example="yohannvessime@gmail.com"
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="Code OTP envoyé",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            404: "Utilisateur non trouvé"
        },
        tags=['Authentification']
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': "Aucun utilisateur avec cet email"}, status=status.HTTP_404_NOT_FOUND)

        # Générer OTP au lieu du lien
        otp_code = user.generate_otp()

        # Email avec OTP
        subject = "Code de vérification pour réinitialiser le mot de passe"
        try:
            html_message = render_to_string("emails/reset_password_otp_email.html", {
                'user': user,
                'otp_code': otp_code,
            })
        except TemplateDoesNotExist:
            html_message = f"""
                <html><body>
                  <p>Bonjour {user.username},</p>
                  <p>Votre code de vérification est : <strong>{otp_code}</strong></p>
                  <p>Ce code expire dans 5 minutes.</p>
                  <p>L'équipe BabiLoc</p>
                </body></html>
            """
        plain_message = f"Bonjour {user.username},\n\nVotre code de vérification est : {otp_code}\n\nCe code expire dans 5 minutes."

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)

        return Response({
            'message': 'Un code de vérification a été envoyé à votre email',
            'user_id': user.id  # Pour la prochaine étape
        })

class ResetPasswordConfirmView(APIView):
    permission_classes = [permissions.AllowAny]  # <- allow anonymous users

    @swagger_auto_schema(
        operation_description="Réinitialiser le mot de passe avec code OTP",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "otp_code", "new_password"],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'otp_code': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        tags=['Authentification']
    )
    def post(self, request):
        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp_code')
        new_password = request.data.get('new_password')

        if not all([user_id, otp_code, new_password]):
            return Response({'error': 'Tous les champs sont requis'}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=404)

        if user.verify_otp(otp_code):
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Mot de passe réinitialisé avec succès'})
        else:
            return Response({'error': 'Code OTP invalide ou expiré'}, status=400)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Inscription d'un nouvel utilisateur",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'email', 'first_name', 'last_name', 'number', 'birthdate', 'password', 'password2'],
            properties={
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom d'utilisateur unique",
                    example="yohann_test"
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="Adresse email",
                    example="yohannvessime@gmail.com"
                ),
                'first_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Prénom",
                    example="Yohann"
                ),
                'last_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom de famille",
                    example="Vessime"
                ),
                'number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Numéro de téléphone",
                    example="+2250701234567"
                ),
                'birthdate': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATE,
                    description="Date de naissance",
                    example="1990-01-01"
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Mot de passe",
                    example="motdepasse123"
                ),
                'password2': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Confirmation du mot de passe",
                    example="motdepasse123"
                ),
                'is_vendor': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Est-ce un vendeur ?",
                    example=False
                ),
                'carte_identite': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Carte d'identité (fichier image)"
                ),
                'permis_conduire': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Permis de conduire (fichier image)"
                ),
            }
        ),
        consumes=['multipart/form-data'],  # ✅ Important : spécifier le type de contenu
        responses={
            201: openapi.Response(
                description="Utilisateur créé avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Données invalides"
        },
        tags=['Authentification']
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Générer le code OTP
            otp_code = user.generate_otp()

            try:
                # Sujet du mail
                subject = "Code d'activation de votre compte"

                # Version HTML du mail
                html_message = render_to_string('emails/activation_otp_email.html', {
                    'user': user,
                    'otp_code': otp_code,
                })

                # Version texte simple
                plain_message = (
                    f"Bonjour {user.username},\n\n"
                    f"Merci de vous être inscrit sur Babiloc.\n"
                    f"Votre code d'activation est : {otp_code}\n\n"
                    f"Ce code expire dans 5 minutes.\n\n"
                    f"L'équipe Babiloc."
                )

                # Création et envoi de l'e-mail
                email_message = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email]
                )
                email_message.attach_alternative(html_message, "text/html")
                email_message.send(fail_silently=False)

                # Réponse de succès
                return Response({
                    'message': 'Compte créé avec succès. Un code d\'activation a été envoyé à votre email.',
                    'user_id': user.id,
                    'email': user.email,
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                # Log the error but don't fail the registration
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
                
                # Return success but inform about email issue
                return Response({
                    'message': 'Compte créé avec succès. Cependant, l\'email d\'activation n\'a pas pu être envoyé. Veuillez demander un nouveau code OTP.',
                    'user_id': user.id,
                    'email': user.email,
                    'email_error': True
                }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Vérifier le code OTP pour activer le compte",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "otp_code"],
            properties={
                'user_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID de l'utilisateur",
                    example=1
                ),
                'otp_code': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Code OTP à 4 chiffres",
                    example="1234"
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Compte activé avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: "Code OTP invalide"
        },
        tags=['Authentification']
    )
    def post(self, request):
        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp_code')

        if not user_id or not otp_code:
            return Response({'error': 'ID utilisateur et code OTP requis'}, status=400)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=404)

        if user.verify_otp(otp_code):
            # Générer les tokens JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Compte activé avec succès',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_vendor': user.is_vendor,
                }
            })
        else:
            return Response({'error': 'Code OTP invalide ou expiré'}, status=400)

class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Renvoyer un nouveau code OTP",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        tags=['Authentification']
    )
    def post(self, request):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': 'ID utilisateur requis'}, status=400)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=404)

        if user.is_active:
            return Response({'error': 'Compte déjà activé'}, status=400)

        # Générer un nouveau code OTP
        otp_code = user.generate_otp()

        # Renvoyer l'email
        subject = "Nouveau code d'activation"
        plain_message = f"Bonjour {user.username},\n\nVotre nouveau code d'activation est : {otp_code}\n\nCe code expire dans 5 minutes."

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        email_message.send(fail_silently=False)

        return Response({'message': 'Nouveau code OTP envoyé'})

class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class DocumentUtilisateurCreateView(generics.CreateAPIView):
    """
    Uploader un document de vérification
    """
    serializer_class = DocumentUtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Uploader un document de vérification",
        # ✅ Remove manual_parameters and use request_body instead
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['nom', 'type_document'],
            properties={
                'nom': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom du document"
                ),
                'type_document': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['carte_identite', 'permis_conduire', 'passeport', 'attestation_travail', 'justificatif_domicile', 'autre'],
                    description="Type de document"
                ),
                'fichier': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_BINARY,
                    description="Fichier document (PDF, DOC, etc.)"
                ),
                'image': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_BINARY,
                    description="Image du document (JPG, PNG, etc.)"
                ),
                'date_expiration': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATE,
                    description="Date d'expiration (YYYY-MM-DD)"
                ),
            }
        ),
        responses={
            201: DocumentUtilisateurSerializer,
            400: "Données invalides",
            401: "Non authentifié"
        },
        tags=['Documents Utilisateur']
    )
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        data['utilisateur'] = request.user.id
        
        serializer = self.get_serializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(utilisateur=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MesDocumentsView(generics.ListAPIView):
    """
    Liste des documents de l'utilisateur connecté
    """
    serializer_class = DocumentUtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer mes documents de vérification",
        responses={
            200: DocumentUtilisateurSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Documents Utilisateur']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        return DocumentUtilisateur.objects.filter(utilisateur=self.request.user)

class DocumentUtilisateurUpdateView(generics.UpdateAPIView):
    """
    Mettre à jour un document utilisateur
    """
    serializer_class = DocumentUtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Fix: Vérifier si c'est un appel Swagger
        if getattr(self, 'swagger_fake_view', False):
            return DocumentUtilisateur.objects.none()
        return DocumentUtilisateur.objects.filter(utilisateur=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Mettre à jour un document",
        consumes=['multipart/form-data'],
        responses={
            200: DocumentUtilisateurSerializer,
            400: "Données invalides",
            401: "Non authentifié",
            404: "Document non trouvé"
        },
        tags=['Documents Utilisateur']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

class DocumentUtilisateurDeleteView(generics.DestroyAPIView):
    """
    Supprimer un document utilisateur
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Fix: Vérifier si c'est un appel Swagger
        if getattr(self, 'swagger_fake_view', False):
            return DocumentUtilisateur.objects.none()
        return DocumentUtilisateur.objects.filter(utilisateur=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Supprimer un document",
        responses={
            204: "Document supprimé",
            401: "Non authentifié",
            404: "Document non trouvé"
        },
        tags=['Documents Utilisateur']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

# Vues pour la modération (admin/staff)
class DocumentsModerationView(generics.ListAPIView):
    """
    Liste des documents en attente de modération
    """
    serializer_class = DocumentUtilisateurSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="Récupérer les documents en attente de modération",
        manual_parameters=[
            openapi.Parameter(
                'statut',
                openapi.IN_QUERY,
                description="Filtrer par statut",
                type=openapi.TYPE_STRING,
                enum=['en_attente', 'approuve', 'refuse', 'expire']
            ),
            openapi.Parameter(
                'type_document',
                openapi.IN_QUERY,
                description="Filtrer par type de document",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: DocumentUtilisateurSerializer(many=True),
            401: "Non authentifié",
            403: "Permission refusée"
        },
        tags=['Modération']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = DocumentUtilisateur.objects.all().select_related('utilisateur')
        
        # Filtres
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut_verification=statut)
        
        type_document = self.request.query_params.get('type_document')
        if type_document:
            queryset = queryset.filter(type_document=type_document)
        
        return queryset.order_by('-date_upload')

class DocumentModerationView(generics.UpdateAPIView):
    """
    Modérer un document (approuver/refuser)
    """
    serializer_class = DocumentModerationSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = DocumentUtilisateur.objects.all()
    
    @swagger_auto_schema(
        operation_description="Modérer un document (approuver/refuser)",
        request_body=DocumentModerationSerializer,
        responses={
            200: DocumentModerationSerializer,
            400: "Données invalides",
            401: "Non authentifié",
            403: "Permission refusée",
            404: "Document non trouvé"
        },
        tags=['Modération']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

# Garder pour compatibilité mais déprécié
class ActivateAccountView(APIView):
    def get(self, request, uidb64, token):
        return Response({'error': 'Cette méthode d\'activation n\'est plus supportée. Utilisez le code OTP.'}, status=400)

class DebugUserStatusView(APIView):
    """Vue temporaire pour déboguer le statut utilisateur"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Déboguer le statut d'un utilisateur",
        manual_parameters=[
            openapi.Parameter(
                'email',
                openapi.IN_QUERY,
                description="Adresse email de l'utilisateur à déboguer",
                type=openapi.TYPE_STRING,
                required=True,
                format=openapi.FORMAT_EMAIL
            ),
        ],
        responses={
            200: openapi.Response(
                description="Informations de debug de l'utilisateur",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'otp_verified': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'otp_code': openapi.Schema(type=openapi.TYPE_STRING),
                        'otp_created_at': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Email requis",
            404: "Utilisateur non trouvé"
        },
        tags=['Debug']
    )
    def get(self, request):
        email = request.query_params.get('email')
        if email:
            try:
                user = CustomUser.objects.get(email=email)
                return Response({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'otp_verified': user.otp_verified,
                    'otp_code': user.otp_code,
                    'otp_created_at': str(user.otp_created_at) if user.otp_created_at else None,
                })
            except CustomUser.DoesNotExist:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)
        return Response({'error': 'Email requis'}, status=400)

# ==================== VUES PARRAINAGE ====================

class ParrainageStatsView(generics.RetrieveAPIView):
    """Statistiques de parrainage pour l'utilisateur connecté"""
    serializer_class = StatistiquesParrainageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class FilleulsListView(generics.ListAPIView):
    """Liste des filleuls de l'utilisateur connecté"""
    serializer_class = FilleulSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.request.user.filleuls.all()


class HistoriqueParrainageView(generics.ListAPIView):
    """Historique des actions de parrainage"""
    serializer_class = HistoriqueParrainageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return HistoriqueParrainage.objects.filter(
            parrain=self.request.user
        ).order_by('-created_at')


class ValidationCodeParrainageView(APIView):
    """Valider un code de parrainage"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Valider un code de parrainage",
        request_body=ValidationCodeParrainageSerializer,
        responses={
            200: openapi.Response(
                description="Code validé avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'parrain': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = ValidationCodeParrainageSerializer(data=request.data)
        if serializer.is_valid():
            try:
                parrain = CustomUser.objects.get(
                    code_parrainage=serializer.validated_data['code_parrainage']
                )
                return Response({
                    'valid': True,
                    'parrain': f"{parrain.first_name} {parrain.last_name}",
                    'message': 'Code de parrainage valide'
                })
            except CustomUser.DoesNotExist:
                return Response({
                    'valid': False,
                    'message': 'Code de parrainage invalide'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenerationCodePromoView(APIView):
    """Générer un code promo de parrainage"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Générer un code promo de parrainage",
        request_body=GenerationCodePromoSerializer,
        responses={
            201: openapi.Response(
                description="Code promo généré avec succès",
                schema=CodePromotionParrainageSerializer
            )
        }
    )
    def post(self, request):
        # Vérifier si l'utilisateur a au moins 1 filleul
        if request.user.nb_parrainages < 1:
            return Response({
                'error': 'Vous devez avoir au moins 1 filleul pour générer un code promo'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = GenerationCodePromoSerializer(data=request.data)
        if serializer.is_valid():
            # Générer un code unique
            while True:
                code = 'PROMO' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not CodePromoParrainage.objects.filter(code=code).exists():
                    break
            
            # Calculer la date d'expiration
            date_expiration = timezone.now() + timedelta(days=serializer.validated_data['duree_jours'])
            
            # Créer le code promo
            code_promo = CodePromoParrainage.objects.create(
                code=code,
                utilisateur=request.user,
                reduction_percent=serializer.validated_data['reduction_percent'],
                montant_min=serializer.validated_data['montant_min'],
                date_expiration=date_expiration
            )
            
            return Response(
                CodePromotionParrainageSerializer(code_promo).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CodesPromoListView(generics.ListAPIView):
    """Liste des codes promo générés par l'utilisateur"""
    serializer_class = CodePromotionParrainageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CodePromoParrainage.objects.filter(
            utilisateur=self.request.user
        ).order_by('-created_at')


class UtilisationCodePromoView(APIView):
    """Utiliser un code promo"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Utiliser un code promo",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['code'],
            properties={
                'code': openapi.Schema(type=openapi.TYPE_STRING, description="Code promo à utiliser"),
                'montant_commande': openapi.Schema(type=openapi.TYPE_NUMBER, description="Montant de la commande"),
            }
        ),
        responses={
            200: openapi.Response(
                description="Code promo utilisé avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'reduction_percent': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'montant_reduction': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def post(self, request):
        code = request.data.get('code')
        montant_commande = request.data.get('montant_commande', 0)
        
        if not code:
            return Response({
                'error': 'Code promo requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            code_promo = CodePromoParrainage.objects.get(code=code)
            
            if not code_promo.is_valid():
                return Response({
                    'error': 'Code promo expiré ou déjà utilisé'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if montant_commande < code_promo.montant_min:
                return Response({
                    'error': f'Montant minimum requis: {code_promo.montant_min} F'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculer la réduction
            montant_reduction = (montant_commande * code_promo.reduction_percent) / 100
            
            # Utiliser le code promo
            code_promo.utiliser(request.user)
            
            return Response({
                'success': True,
                'reduction_percent': code_promo.reduction_percent,
                'montant_reduction': montant_reduction,
                'message': 'Code promo appliqué avec succès'
            })
            
        except CodePromoParrainage.DoesNotExist:
            return Response({
                'error': 'Code promo invalide'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parrainage_dashboard(request):
    """Dashboard du parrainage avec toutes les informations"""
    user = request.user
    
    # Statistiques générales
    stats = {
        'code_parrainage': user.code_parrainage,
        'nb_parrainages': user.nb_parrainages,
        'recompense_parrainage': user.recompense_parrainage,
        'recompenses_totales': user.get_recompenses_parrainage(),
    }
    
    # Filleuls
    filleuls = FilleulSerializer(user.filleuls.all(), many=True).data
    
    # Historique récent
    historique = HistoriqueParrainageSerializer(
        user.historique_parrainage.all()[:10], 
        many=True
    ).data
    
    # Codes promo actifs
    codes_promo = CodePromotionParrainageSerializer(
        user.codes_promo_parrainage.filter(
            utilise=False,
            date_expiration__gt=timezone.now()
        ),
        many=True
    ).data
    
    return Response({
        'stats': stats,
        'filleuls': filleuls,
        'historique': historique,
        'codes_promo_actifs': codes_promo
    })


class MonParrainageView(generics.RetrieveAPIView):
    """Vue pour récupérer les informations de parrainage de l'utilisateur"""
    
    serializer_class = ParrainageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer mes informations de parrainage",
        responses={
            200: ParrainageSerializer,
            401: "Non authentifié"
        },
        tags=['Parrainage']
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class MesFilleulsView(generics.ListAPIView):
    """Vue pour lister mes filleuls"""
    
    serializer_class = FilleulSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Lister mes filleuls",
        responses={
            200: FilleulSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Parrainage']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        return self.request.user.filleuls.all().order_by('-date_parrainage')


class HistoriqueParrainageView(generics.ListAPIView):
    """Vue pour l'historique de parrainage"""
    
    serializer_class = HistoriqueParrainageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Historique de mes gains de parrainage",
        manual_parameters=[
            openapi.Parameter(
                'type_action',
                openapi.IN_QUERY,
                description="Filtrer par type d'action",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'statut',
                openapi.IN_QUERY,
                description="Filtrer par statut",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: HistoriqueParrainageSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Parrainage']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = HistoriqueParrainage.objects.filter(
            parrain=self.request.user
        ).order_by('-date_action')
        
        # Filtres
        type_action = self.request.query_params.get('type_action')
        if type_action:
            queryset = queryset.filter(type_action=type_action)
        
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut_recompense=statut)
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_description="Générer un code promo de parrainage",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'pourcentage_reduction': openapi.Schema(type=openapi.TYPE_INTEGER, default=10),
            'duree_jours': openapi.Schema(type=openapi.TYPE_INTEGER, default=30),
        }
    ),
    responses={
        201: CodePromotionParrainageSerializer,
        400: "Données invalides"
    },
    tags=['Parrainage']
)
def generer_code_promo(request):
    """Générer un code promo de parrainage pour l'utilisateur"""
    
    user = request.user
    pourcentage = request.data.get('pourcentage_reduction', 10)
    duree_jours = request.data.get('duree_jours', 30)
    
    # Vérifier si l'utilisateur peut générer un code
    if user.points_parrainage < 100:  # Minimum 100 points requis
        return Response({
            'error': 'Vous devez avoir au moins 100 points de parrainage'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Générer le code
    import string
    code = f"PARRAIN{user.id}{random.randint(100, 999)}"
    
    # Créer le code promo
    code_promo = CodePromoParrainage.objects.create(
        code=code,
        parrain=user,
        pourcentage_reduction=pourcentage,
        date_expiration=timezone.now() + timedelta(days=duree_jours)
    )
    
    # Déduire les points
    user.points_parrainage -= 100
    user.save()
    
    serializer = CodePromotionParrainageSerializer(code_promo)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_description="Statistiques de parrainage",
    responses={
        200: StatistiquesParrainageSerializer,
        401: "Non authentifié"
    },
    tags=['Parrainage']
)
def statistiques_parrainage(request):
    """Statistiques détaillées de parrainage"""
    
    user = request.user
    
    # Statistiques de base
    filleuls_total = user.filleuls.count()
    filleuls_actifs = user.filleuls.filter(parrainage_actif=True).count()
    
    # Revenus
    revenus_total = user.historiques_parrainage.aggregate(
        total=Sum('montant_recompense')
    )['total'] or 0
    
    points_total = user.points_parrainage
    
    # Ce mois
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    revenus_ce_mois = user.historiques_parrainage.filter(
        date_action__gte=debut_mois
    ).aggregate(total=Sum('montant_recompense'))['total'] or 0
    
    filleuls_ce_mois = user.filleuls.filter(
        date_parrainage__gte=debut_mois
    ).count()
    
    # Évolution mensuelle (6 derniers mois)
    evolution_mensuelle = []
    for i in range(6):
        date_debut = (timezone.now() - timedelta(days=30*i)).replace(day=1)
        date_fin = (date_debut + timedelta(days=32)).replace(day=1)
        
        revenus_mois = user.historiques_parrainage.filter(
            date_action__gte=date_debut,
            date_action__lt=date_fin
        ).aggregate(total=Sum('montant_recompense'))['total'] or 0
        
        filleuls_mois = user.filleuls.filter(
            date_parrainage__gte=date_debut,
            date_parrainage__lt=date_fin
        ).count()
        
        evolution_mensuelle.append({
            'mois': date_debut.strftime('%Y-%m'),
            'revenus': revenus_mois,
            'nouveaux_filleuls': filleuls_mois
        })
    
    # Top actions
    top_actions = user.historiques_parrainage.values('type_action').annotate(
        count=Count('id'),
        total_revenus=Sum('montant_recompense')
    ).order_by('-total_revenus')[:5]
    
    data = {
        'nombre_filleuls_total': filleuls_total,
        'nombre_filleuls_actifs': filleuls_actifs,
        'revenus_total': revenus_total,
        'points_total': points_total,
        'revenus_ce_mois': revenus_ce_mois,
        'filleuls_ce_mois': filleuls_ce_mois,
        'evolution_mensuelle': evolution_mensuelle,
        'top_actions': list(top_actions)
    }
    
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@swagger_auto_schema(
    operation_description="Vérifier un code de parrainage",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['code_parrainage'],
        properties={
            'code_parrainage': openapi.Schema(type=openapi.TYPE_STRING)
        }
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'parrain_info': openapi.Schema(type=openapi.TYPE_OBJECT),
                'bonus_inscription': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        400: "Code invalide"
    },
    tags=['Parrainage']
)
def verifier_code_parrainage(request):
    """Vérifier la validité d'un code de parrainage"""
    
    code = request.data.get('code_parrainage')
    if not code:
        return Response({
            'error': 'Code de parrainage requis'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        parrain = CustomUser.objects.get(code_parrainage=code)
        return Response({
            'valid': True,
            'parrain_info': {
                'id': parrain.id,
                'username': parrain.username,
                'first_name': parrain.first_name,
                'last_name': parrain.last_name
            },
            'bonus_inscription': 5000  # Bonus pour le nouveau utilisateur
        })
    except CustomUser.DoesNotExist:
        return Response({
            'valid': False,
            'error': 'Code de parrainage invalide'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_description="Demander le retrait des gains de parrainage",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['montant'],
        properties={
            'montant': openapi.Schema(type=openapi.TYPE_NUMBER),
            'mode_paiement': openapi.Schema(type=openapi.TYPE_STRING)
        }
    ),
    responses={
        200: "Demande de retrait enregistrée",
        400: "Données invalides"
    },
    tags=['Parrainage']
)
def demander_retrait(request):
    """Demander le retrait des gains de parrainage"""
    
    user = request.user
    montant = request.data.get('montant')
    mode_paiement = request.data.get('mode_paiement', 'mobile_money')
    
    if not montant or montant <= 0:
        return Response({
            'error': 'Montant invalide'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Vérifier le solde disponible
    solde_disponible = user.get_revenus_parrainage()
    if montant > solde_disponible:
        return Response({
            'error': f'Solde insuffisant. Disponible: {solde_disponible} FCFA'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Créer la demande de retrait (vous devrez implémenter le modèle)
    # DemandeRetrait.objects.create(
    #     user=user,
    #     montant=montant,
    #     mode_paiement=mode_paiement,
    #     statut='en_attente'
    # )
    
    return Response({
        'message': 'Demande de retrait enregistrée',
        'montant': montant,
        'mode_paiement': mode_paiement
    })


# ==================== VUES POUR LES CODES PROMO ====================

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@swagger_auto_schema(
    operation_description="Valider un code promo de parrainage",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['code'],
        properties={
            'code': openapi.Schema(type=openapi.TYPE_STRING),
            'montant_reservation': openapi.Schema(type=openapi.TYPE_NUMBER)
        }
    ),
    tags=['Parrainage']
)
def valider_code_promo(request):
    """Valider un code promo de parrainage"""
    
    code = request.data.get('code')
    montant_reservation = request.data.get('montant_reservation', 0)
    
    try:
        code_promo = CodePromoParrainage.objects.get(code=code)
        
        if not code_promo.is_valid():
            return Response({
                'valid': False,
                'error': 'Code expiré ou déjà utilisé'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculer la réduction
        if code_promo.pourcentage_reduction:
            reduction = (montant_reservation * code_promo.pourcentage_reduction) / 100
        else:
            reduction = code_promo.montant_reduction or 0
        
        return Response({
            'valid': True,
            'reduction': reduction,
            'pourcentage': code_promo.pourcentage_reduction,
            'parrain': code_promo.parrain.username
        })
        
    except CodePromoParrainage.DoesNotExist:
        return Response({
            'valid': False,
            'error': 'Code promo invalide'
        }, status=status.HTTP_400_BAD_REQUEST)

# ==================== DEVENIR VENDOR ====================

class DevenirVendorView(APIView):
    """
    Demande pour devenir vendor (propriétaire/hôte)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Soumettre une demande pour devenir propriétaire",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['structure_type'],
            properties={
                # ✅ Champs personnels (ajoutés)
                'last_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom de famille"
                ),
                'first_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Prénom"
                ),
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="Adresse email"
                ),
                'phone_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Numéro de téléphone personnel"
                ),
                # ✅ Type de structure
                'structure_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['particulier', 'agence', 'societe'],
                    description="Type de structure"
                ),
                # ✅ Champs entreprise (existants)
                'agence_nom': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom de l'agence (si applicable)"
                ),
                'agence_adresse': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Adresse complète (si applicable)"
                ),
                'representant_telephone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Téléphone représentant légal"
                ),
            }
        ),
        consumes=['multipart/form-data'],
        responses={
            201: openapi.Response(
                description="Demande soumise avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'structure_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Données invalides",
            401: "Non authentifié"
        },
        tags=['Vendor']
    )
    def post(self, request):
        user = request.user
        structure_type = request.data.get('structure_type', 'particulier')
        
        # Vérifier si l'utilisateur n'est pas déjà vendor
        if user.is_vendor:
            return Response({
                'error': 'Vous êtes déjà propriétaire/hôte'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ Récupérer et mettre à jour les informations personnelles
        last_name = request.data.get('last_name')
        first_name = request.data.get('first_name')
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')
        
        # Mettre à jour le profil utilisateur si de nouvelles infos sont fournies
        updated = False
        if last_name and last_name != user.last_name:
            user.last_name = last_name
            updated = True
        if first_name and first_name != user.first_name:
            user.first_name = first_name
            updated = True
        if email and email != user.email:
            user.email = email
            updated = True
        if phone_number and phone_number != user.number:
            user.number = phone_number
            updated = True
        
        if updated:
            user.save()
        
        # Créer le document principal (pièce d'identité)
        piece_identite = request.FILES.get('piece_identite')
        if piece_identite:
            DocumentUtilisateur.objects.create(
                utilisateur=user,
                nom=f"Pièce d'identité - Demande vendor",
                type_document='carte_identite',
                fichier=piece_identite,
                structure_type=structure_type,
                agence_nom=request.data.get('agence_nom', ''),
                agence_adresse=request.data.get('agence_adresse', ''),
                representant_telephone=request.data.get('representant_telephone', ''),
                statut_verification='en_attente'
            )
        
        # Pour les entreprises, ajouter les documents supplémentaires
        if structure_type in ['agence', 'societe']:
            # Pièce d'identité du représentant légal
            piece_representant = request.FILES.get('piece_identite_representant')
            if piece_representant:
                DocumentUtilisateur.objects.create(
                    utilisateur=user,
                    nom=f"Pièce d'identité représentant légal",
                    type_document='carte_identite',
                    fichier=piece_representant,
                    structure_type=structure_type,
                    agence_nom=request.data.get('agence_nom', ''),
                    agence_adresse=request.data.get('agence_adresse', ''),
                    representant_telephone=request.data.get('representant_telephone', ''),
                    statut_verification='en_attente'
                )
            
            # Document RCCM
            rccm = request.FILES.get('document_rccm')
            if rccm:
                DocumentUtilisateur.objects.create(
                    utilisateur=user,
                    nom=f"Document RCCM - {request.data.get('agence_nom', '')}",
                    type_document='rccm',
                    fichier=rccm,
                    structure_type=structure_type,
                    agence_nom=request.data.get('agence_nom', ''),
                    agence_adresse=request.data.get('agence_adresse', ''),
                    representant_telephone=request.data.get('representant_telephone', ''),
                    statut_verification='en_attente'
                )
        
        # Envoyer notification aux admins
        try:
            from django.core.mail import send_mail
            send_mail(
                subject=f'Nouvelle demande vendor - {user.username}',
                message=f'Une nouvelle demande pour devenir propriétaire a été soumise par {user.get_full_name() or user.username}\n\nType: {structure_type}\nAgence: {request.data.get("agence_nom", "N/A")}\nEmail: {email}\nTéléphone: {phone_number}',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=True
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur envoi email notification: {e}")
        
        return Response({
            'message': 'Demande soumise avec succès',
            'structure_type': structure_type,
            'status': 'en_attente_verification',
            'profile_updated': updated  # ✅ Indiquer si le profil a été mis à jour
        }, status=status.HTTP_201_CREATED)

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@staff_member_required
def vendor_admin_dashboard(request):
    """Dashboard admin pour gérer les demandes vendor"""
    # Statistiques des demandes vendor
    demandes_en_attente = DocumentUtilisateur.objects.filter(
        nom__icontains='Demande vendor',
        statut_verification='en_attente'
    ).count()
    
    demandes_approuvees = DocumentUtilisateur.objects.filter(
        nom__icontains='Demande vendor',
        statut_verification='approuve'
    ).count()
    
    demandes_refusees = DocumentUtilisateur.objects.filter(
        nom__icontains='Demande vendor',
        statut_verification='refuse'
    ).count()
    
    # Dernières demandes
    dernieres_demandes = DocumentUtilisateur.objects.filter(
        nom__icontains='Demande vendor'
    ).select_related('utilisateur').order_by('-date_upload')[:10]
    
    context = {
        'demandes_en_attente': demandes_en_attente,
        'demandes_approuvees': demandes_approuvees,
        'demandes_refusees': demandes_refusees,
        'dernieres_demandes': dernieres_demandes,
        'total_demandes': demandes_en_attente + demandes_approuvees + demandes_refusees,
    }
    
    return render(request, 'admin/vendor_dashboard.html', context)

@staff_member_required
def vendor_requests_list(request):
    """Liste paginée des demandes vendor"""
    status_filter = request.GET.get('status', 'all')
    structure_filter = request.GET.get('structure', 'all')
    
    # Base queryset
    queryset = DocumentUtilisateur.objects.filter(
        nom__icontains='Demande vendor'
    ).select_related('utilisateur', 'moderateur')
    
    # Filtres
    if status_filter != 'all':
        queryset = queryset.filter(statut_verification=status_filter)
    
    if structure_filter != 'all':
        queryset = queryset.filter(structure_type=structure_filter)
    
    # Regrouper par utilisateur pour éviter les doublons
    demandes = {}
    for doc in queryset.order_by('-date_upload'):
        user_id = doc.utilisateur.id
        if user_id not in demandes:
            # Compter tous les documents de cette demande
            docs_count = DocumentUtilisateur.objects.filter(
                utilisateur=doc.utilisateur,
                nom__icontains='Demande vendor'
            ).count()
            
            demandes[user_id] = {
                'document': doc,
                'documents_count': docs_count,
                'user': doc.utilisateur,
            }
    
    context = {
        'demandes': list(demandes.values()),
        'status_filter': status_filter,
        'structure_filter': structure_filter,
    }
    
    return render(request, 'admin/vendor_requests.html', context)

@staff_member_required
@csrf_exempt
def vendor_action(request):
    """Actions sur les demandes vendor (approuver/refuser)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        action = data.get('action')  # 'approve' ou 'reject'
        
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Récupérer tous les documents de cette demande
            documents = DocumentUtilisateur.objects.filter(
                utilisateur=user,
                nom__icontains='Demande vendor'
            )
            
            if action == 'approve':
                # Approuver tous les documents
                documents.update(
                    statut_verification='approuve',
                    moderateur=request.user
                )
                
                # Activer le statut vendor
                user.is_vendor = True
                user.est_verifie = True
                user.save()
                
                # Email de confirmation
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject='🎉 Demande vendor approuvée - BabiLoc',
                        message=f'Félicitations {user.get_full_name() or user.username} !\n\nVotre demande pour devenir propriétaire/hôte a été approuvée.\n\nVous pouvez maintenant publier vos biens sur BabiLoc.\n\nL\'équipe BabiLoc',
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=True
                    )
                except:
                    pass
                
                return JsonResponse({
                    'success': True,
                    'message': f'Demande de {user.get_full_name() or user.username} approuvée avec succès'
                })
            
            elif action == 'reject':
                # Refuser tous les documents
                documents.update(
                    statut_verification='refuse',
                    moderateur=request.user,
                    commentaire_moderateur="Demande refusée par l'administration"
                )
                
                # Email de refus
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject='❌ Demande vendor refusée - BabiLoc',
                        message=f'Bonjour {user.get_full_name() or user.username},\n\nNous regrettons de vous informer que votre demande pour devenir propriétaire/hôte a été refusée.\n\nRaison: Documents non conformes ou incomplets.\n\nVous pouvez soumettre une nouvelle demande avec des documents mis à jour.\n\nL\'équipe BabiLoc',
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=True
                    )
                except:
                    pass
                
                return JsonResponse({
                    'success': True,
                    'message': f'Demande de {user.get_full_name() or user.username} refusée'
                })
            
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

class AccountDeletionLogListView(generics.ListAPIView):
    """
    Liste des suppressions de compte (admin uniquement)
    Filtres:
      - q: recherche email/username
      - user_id: ID utilisateur supprimé
      - performed_by: ID admin qui a effectué l’action
      - hard_delete: true/false
      - from, to: ISO date (YYYY-MM-DD)
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AccountDeletionLogSerializer

    @swagger_auto_schema(
        operation_description="Lister les suppressions de compte (admin)",
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Rechercher email/username"),
            openapi.Parameter('user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="ID utilisateur supprimé"),
            openapi.Parameter('performed_by', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="ID de l'admin"),
            openapi.Parameter('hard_delete', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="true/false"),
            openapi.Parameter('from', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Date début YYYY-MM-DD"),
            openapi.Parameter('to', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Date fin YYYY-MM-DD"),
        ],
        responses={200: AccountDeletionLogSerializer(many=True)},
        tags=['Administration']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = AccountDeletionLog.objects.all()
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(models.Q(email__icontains=q) | models.Q(username__icontains=q))
        user_id = self.request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        performed_by = self.request.query_params.get('performed_by')
        if performed_by:
            qs = qs.filter(performed_by_id=performed_by)
        hard_delete = self.request.query_params.get('hard_delete')
        if hard_delete is not None:
            val = str(hard_delete).lower() in ['1', 'true', 'yes']
            qs = qs.filter(hard_delete=val)
        date_from = self.request.query_params.get('from')
        if date_from:
            qs = qs.filter(deleted_at__date__gte=date_from)
        date_to = self.request.query_params.get('to')
        if date_to:
            qs = qs.filter(deleted_at__date__lte=date_to)
        return qs.order_by('-deleted_at')

class AccountDeletionLogDetailView(generics.RetrieveAPIView):
    """Détail d’une suppression (admin uniquement)"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AccountDeletionLogSerializer
    queryset = AccountDeletionLog.objects.all()

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Changer le mot de passe (auth requis)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["old_password", "new_password"],
            properties={
                'old_password': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        tags=['Authentification']
    )
    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'Tous les champs sont requis'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({'error': 'Ancien mot de passe incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Mot de passe mis à jour avec succès'}, status=status.HTTP_200_OK)

class DeleteAccountView(APIView):
    """
    Supprimer définitivement le compte de l'utilisateur connecté.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Supprimer le compte de l'utilisateur connecté",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['confirm'],
            properties={
                'confirm': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Confirmer la suppression"),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description="Mot de passe (optionnel si non défini)"),
                'hard_delete': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Suppression physique (défaut: false)"),
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description="Raison fournie par l'utilisateur")
            }
        ),
        responses={
            200: openapi.Response(
                description="Compte supprimé (soft) ou désactivé",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'mode': openapi.Schema(type=openapi.TYPE_STRING, enum=['soft', 'hard'])
                    }
                )
            ),
            204: "Compte supprimé (hard)",
            400: "Confirmation manquante ou mot de passe incorrect",
            401: "Non authentifié"
        },
        tags=['Profil']
    )
    def post(self, request):
        user = request.user
        confirm = request.data.get('confirm')
        if not (confirm is True or str(confirm).lower() in ['true', '1', 'yes', 'on']):
            return Response({'error': 'Confirmation requise'}, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get('password')
        if user.has_usable_password() and password:
            if not user.check_password(password):
                return Response({'error': 'Mot de passe incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        # Récupérer les champs manquants
        reason = request.data.get('reason', '')  # <- fix
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
            or ''
        )  # <- fix

        # Forcer le hard delete à False (aucun choix côté front)
        hard_delete = False  # <- force

        # Compter les objets liés (pour audit)
        try:
            from reservation.models import Reservation, Favori, Avis
            reservations_count = Reservation.objects.filter(user=user).count()
            favoris_count = Favori.objects.filter(user=user).count()
            avis_count = Avis.objects.filter(user=user).count()
        except Exception:
            reservations_count = favoris_count = avis_count = 0

        # Créer le log d'audit AVANT suppression/anonymisation
        AccountDeletionLog.objects.create(
            user_id=user.id,
            email=user.email,
            username=user.username,
            is_vendor=user.is_vendor,
            reason=reason,
            ip_address=ip,
            reservations_count=reservations_count,
            favoris_count=favoris_count,
            avis_count=avis_count,
            hard_delete=hard_delete,
            performed_by=request.user
        )

        uid = user.id

        if hard_delete:
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # Soft delete: désactiver et anonymiser
        user.is_active = False
        user.is_vendor = False
        user.est_verifie = False
        user.first_name = ''
        user.last_name = ''
        user.number = None
        user.otp_code = None
        user.username = f"deleted_user_{uid}"
        user.email = f"deleted_{uid}@deleted.local"

        # Nettoyer médias si présents
        try:
            if getattr(user, 'photo_profil', None):
                user.photo_profil.delete(save=False)
                user.photo_profil = None
            if getattr(user, 'image_banniere', None):
                user.image_banniere.delete(save=False)
                user.image_banniere = None
        except Exception:
            pass

        # Sauvegarde sécurisée: inclure seulement les champs existants
        update_fields = [
            'is_active', 'is_vendor', 'est_verifie', 'first_name', 'last_name',
            'number', 'otp_code', 'username', 'email'
        ]
        for extra in ['photo_profil', 'image_banniere']:
            if hasattr(user, extra):
                update_fields.append(extra)

        user.save(update_fields=update_fields)

        return Response({'message': 'Compte désactivé et anonymisé', 'user_id': uid, 'mode': 'soft'}, status=status.HTTP_200_OK)

class DeleteAccountRequestOTPView(APIView):
    """
    Étape 1: Demander la suppression (génère un OTP et l'envoie par email)
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Demander un OTP pour confirmer la suppression du compte",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description="Raison (optionnelle)"),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description="Mot de passe (si requis)"),
            }
        ),
        responses={200: "OTP envoyé par email"},
        tags=['Profil']
    )
    def post(self, request):
        user = request.user
        reason = request.data.get('reason', '')
        password = request.data.get('password')

        # Vérif mot de passe si l'utilisateur en a un et qu'il a fourni le champ
        if user.has_usable_password() and password:
            if not user.check_password(password):
                return Response({'error': 'Mot de passe incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        # Générer un OTP spécifique (sans toucher à otp_verified)
        otp_code = str(random.randint(1000, 9999))
        user.otp_code = otp_code
        user.otp_created_at = timezone.now()
        user.save(update_fields=['otp_code', 'otp_created_at'])

        # Envoi email OTP
        subject = "Confirmez la suppression de votre compte - Code OTP"
        try:
            html_message = render_to_string('emails/delete_account_otp_email.html', {
                'user': user,
                'otp_code': otp_code,
                'reason': reason,
            })
        except TemplateDoesNotExist:
            html_message = f"""
                <html><body>
                    <p>Bonjour {user.get_full_name() or user.username},</p>
                    <p>Vous avez demandé la suppression de votre compte.</p>
                    <p>Votre code de confirmation est : <strong>{otp_code}</strong></p>
                    <p>Ce code expire dans 2 minutes.</p>
                    <p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>
                    <p>L'équipe BabiLoc</p>
                </body></html>
            """

        plain_message = (
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            f"Vous avez demandé la suppression de votre compte.\n"
            f"Votre code de confirmation est : {otp_code}\n"
            f"Ce code expire dans 2 minutes.\n\n"
            f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n"
            f"L'équipe BabiLoc"
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=True)

        return Response({'message': 'OTP envoyé par email'}, status=status.HTTP_200_OK)


class DeleteAccountConfirmOTPView(APIView):
    """
    Étape 2: Confirmer avec l’OTP et exécuter la suppression (soft delete)
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Confirmer la suppression avec l’OTP",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["otp_code", "confirm"],
            properties={
                'otp_code': openapi.Schema(type=openapi.TYPE_STRING),
                'confirm': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'reason': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(
                description="Compte désactivé et anonymisé",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'mode': openapi.Schema(type=openapi.TYPE_STRING, enum=['soft'])
                    }
                )
            ),
            400: "OTP invalide/expiré ou confirmation manquante",
        },
        tags=['Profil']
    )
    def post(self, request):
        user = request.user
        confirm = request.data.get('confirm')
        if not (confirm is True or str(confirm).lower() in ['true', '1', 'yes', 'on']):
            return Response({'error': 'Confirmation requise'}, status=status.HTTP_400_BAD_REQUEST)

        otp_code = request.data.get('otp_code')
        if not otp_code:
            return Response({'error': 'Code OTP requis'}, status=status.HTTP_400_BAD_REQUEST)

        # Valider l’OTP via la fenêtre de validité existante
        if not (str(user.otp_code) == str(otp_code) and user.is_otp_valid()):
            return Response({'error': 'Code OTP invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        # Nettoyer l’OTP
        user.otp_code = None
        user.otp_created_at = None
        user.save(update_fields=['otp_code', 'otp_created_at'])

        # Récupérer infos pour audit
        reason = request.data.get('reason', 'confirmed_via_otp')
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
            or ''
        )
        hard_delete = False  # on force soft delete

        # Compter les objets liés (audit)
        try:
            from reservation.models import Reservation, Favori, Avis
            reservations_count = Reservation.objects.filter(user=user).count()
            favoris_count = Favori.objects.filter(user=user).count()
            avis_count = Avis.objects.filter(user=user).count()
        except Exception:
            reservations_count = favoris_count = avis_count = 0

        # Journaliser avant anonymisation
        AccountDeletionLog.objects.create(
            user_id=user.id,
            email=user.email,
            username=user.username,
            is_vendor=user.is_vendor,
            reason=reason,
            ip_address=ip,
            reservations_count=reservations_count,
            favoris_count=favoris_count,
            hard_delete=hard_delete,
            performed_by=request.user
        )

        # Soft delete (réutilise la logique de [`Auths.views.DeleteAccountView`](Auths/views.py))
        uid = user.id
        user.is_active = False
        user.is_vendor = False
        user.est_verifie = False
        user.first_name = ''
        user.last_name = ''
        user.number = None
        user.username = f"deleted_user_{uid}"
        user.email = f"deleted_{uid}@deleted.local"

        try:
            if getattr(user, 'photo_profil', None):
                user.photo_profil.delete(save=False)
                user.photo_profil = None
            if getattr(user, 'image_banniere', None):
                user.image_banniere.delete(save=False)
                user.image_banniere = None
        except Exception:
            pass

        update_fields = [
            'is_active', 'is_vendor', 'est_verifie', 'first_name', 'last_name',
            'number', 'username', 'email'
        ]
        for extra in ['photo_profil', 'image_banniere']:
            if hasattr(user, extra):
                update_fields.append(extra)

        user.save(update_fields=update_fields)

        return Response({'message': 'Compte désactivé et anonymisé', 'user_id': uid, 'mode': 'soft'}, status=status.HTTP_200_OK)

class DocumentUniverselUploadView(generics.CreateAPIView):
    """
    Upload universel: crée ou met à jour le document de vérification d'un type donné.
    Si un document (utilisateur, type_document) existe déjà, il est mis à jour.
    """
    serializer_class = DocumentUtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Créer ou mettre à jour un document utilisateur (upsert)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['nom', 'type_document'],
            properties={
                'nom': openapi.Schema(type=openapi.TYPE_STRING),
                'type_document': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['carte_identite', 'permis_conduire', 'passeport', 'attestation_travail',
                          'justificatif_domicile', 'rccm', 'autre']
                ),
                'fichier': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
                'image': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
                'date_expiration': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            }
        ),
        consumes=['multipart/form-data'],
        responses={
            200: DocumentUtilisateurSerializer,
            201: DocumentUtilisateurSerializer,
            400: "Données invalides",
            401: "Non authentifié"
        },
        tags=['Documents Utilisateur']
    )
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        data['utilisateur'] = request.user.id
        type_doc = data.get('type_document')

        if not type_doc:
            return Response({'error': 'type_document requis'}, status=status.HTTP_400_BAD_REQUEST)

        # Chercher un document existant de ce type
        instance = DocumentUtilisateur.objects.filter(
            utilisateur=request.user,
            type_document=type_doc
        ).first()

        context = {'request': request}

        if instance:
            # Mise à jour
            serializer = self.get_serializer(instance, data=data, partial=True, context=context)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Création
            serializer = self.get_serializer(data=data, context=context)
            if serializer.is_valid():
                serializer.save(utilisateur=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)