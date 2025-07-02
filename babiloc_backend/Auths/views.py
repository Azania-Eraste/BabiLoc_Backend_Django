from .models import CustomUser
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from .serializers import RegisterSerializer, MyTokenObtainPairSerializer, UserSerializer, OTPVerificationSerializer
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

# Garder pour compatibilité mais déprécié
class ActivateAccountView(APIView):
    def get(self, request, uidb64, token):
        return Response({'error': 'Cette méthode d\'activation n\'est plus supportée. Utilisez le code OTP.'}, status=400)


