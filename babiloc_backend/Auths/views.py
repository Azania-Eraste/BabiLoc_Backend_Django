from .models import CustomUser, DocumentUtilisateur,HistoriqueParrainage,CodePromoParrainage  # Ajouter DocumentUtilisateur
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from .serializers import (
    RegisterSerializer, MyTokenObtainPairSerializer, UserSerializer, 
    OTPVerificationSerializer, DocumentUtilisateurSerializer, 
    DocumentModerationSerializer, FilleulSerializer, 
    HistoriqueParrainageSerializer, ParrainageSerializer, 
    CodePromotionParrainageSerializer, StatistiquesParrainageSerializer,
    ValidationCodeParrainageSerializer, GenerationCodePromoSerializer
)
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import EmailMultiAlternatives
from rest_framework import permissions
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import HttpResponse
import random
import string
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes

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
        operation_description="Authentification pour obtenir le JWT",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom d'utilisateur",
                    example="yohannvessime"
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
                        'code_parrainage': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_vendor': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    }
                )
            ),
            400: "Compte non activé",
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

            username = request.data.get('username')
            print(f"Username: {username}")  # Debugging line
            if username:
                try:
                    user = CustomUser.objects.get(username=username)
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
        print(f"🔍 MeView - Utilisateur connecté: {user.username} (ID: {user.id})")
        serializer = UserSerializer(user)
        print(f"✅ MeView - Données sérialisées pour: {user.username}")
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        user = request.user
        print(f"🔄 MeView PATCH - Utilisateur: {user.username} (ID: {user.id})")
        print(f"📝 Données reçues: {request.data}")
        
        # Champs autorisés à être mis à jour
        allowed_fields = ['first_name', 'last_name', 'number', 'birthdate']
        
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
                print(f"✏️ {field} mis à jour: {request.data[field]}")
        
        try:
            user.save()
            print(f"💾 Profil sauvegardé pour: {user.username}")
            serializer = UserSerializer(user)
            return Response({
                'success': True,
                'message': 'Profil mis à jour avec succès',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ Erreur sauvegarde profil: {e}")
            return Response({
                'success': False,
                'error': 'Erreur lors de la sauvegarde du profil'
            }, status=status.HTTP_400_BAD_REQUEST)

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
        subject = "Code de vérification pour réinitialisation"
        html_message = render_to_string("emails/reset_password_otp_email.html", {
            'user': user,
            'otp_code': otp_code,
        })
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
                ),
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
    import random
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


class BecomeVendorView(APIView):
    """
    Endpoint pour promouvoir un utilisateur en vendeur/hôte
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Promouvoir l'utilisateur connecté en vendeur/hôte",
        responses={
            200: openapi.Response(
                description="Promotion réussie",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_vendor': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    }
                )
            ),
            400: openapi.Response(description="L'utilisateur est déjà vendeur")
        },
        tags=["Authentification"]
    )
    def patch(self, request):
        user = request.user
        print(f"=== BECOME VENDOR REQUEST ===")
        print(f"User: {user.username} (ID: {user.id})")
        print(f"Current is_vendor: {user.is_vendor}")
        print(f"Request data: {request.data}")
        
        if user.is_vendor:
            print(f"❌ User {user.username} is already a vendor")
            return Response({
                'success': False,
                'message': 'Vous êtes déjà un vendeur/hôte',
                'is_vendor': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Promouvoir l'utilisateur en vendeur
        print(f"✅ Promoting user {user.username} to vendor")
        user.is_vendor = True
        user.save()
        
        # Générer un nouveau token avec les nouvelles permissions
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        print(f"✅ User {user.username} successfully promoted to vendor")
        return Response({
            'success': True,
            'message': 'Vous êtes maintenant un vendeur/hôte !',
            'is_vendor': True,
            'access': access_token,  # Nouveau token avec les permissions mises à jour
        }, status=status.HTTP_200_OK)