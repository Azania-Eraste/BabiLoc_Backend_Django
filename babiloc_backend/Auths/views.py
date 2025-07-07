from .models import CustomUser, DocumentUtilisateur  # Ajouter DocumentUtilisateur
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from .serializers import RegisterSerializer, MyTokenObtainPairSerializer, UserSerializer, OTPVerificationSerializer, DocumentUtilisateurSerializer, DocumentModerationSerializer
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

User = get_user_model()

def welcome_view(request):
    return HttpResponse("<h1>Bienvenue sur Babiloc !</h1><p>Votre plateforme de location.</p>")

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    @swagger_auto_schema(
        operation_description="Authentification pour obtenir le JWT",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(
                description="Token JWT et infos utilisateur",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_vendor': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    }
                )
            ),
            401: "Identifiants invalides"
        },
        tags=['Authentification']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

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


