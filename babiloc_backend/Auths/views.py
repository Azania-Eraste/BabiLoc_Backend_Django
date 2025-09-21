from .models import CustomUser
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from .serializers import RegisterSerializer, MyTokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import generate_activation_link
from django.core.mail import EmailMultiAlternatives
from rest_framework import permissions
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


User = get_user_model()


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
        serializer = RegisterSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': "Aucun utilisateur avec cet email"}, status=status.HTTP_404_NOT_FOUND)

        # Générer token + lien
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"{request.scheme}://{request.get_host()}/api/auth/reset-password/{uid}/{token}/"

        # Email
        subject = "Réinitialisation de votre mot de passe"
        html_message = render_to_string("emails/reset_password_email.html", {
            'user': user,
            'reset_link': reset_link,
        })
        plain_message = f"Bonjour {user.username},\n\nCliquez sur ce lien pour réinitialiser votre mot de passe : {reset_link}"

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)

        return Response({'message': 'Un lien de réinitialisation a été envoyé à votre email'})
    

class ResetPasswordConfirmView(APIView):
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Lien invalide'}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Token invalide ou expiré'}, status=400)

        new_password = request.data.get('password')
        if not new_password:
            return Response({'error': 'Mot de passe requis'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Mot de passe réinitialisé avec succès'})

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny] 
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            # Générer le lien d'activation
            activation_link = generate_activation_link(user, request)

            # Sujet du mail
            subject = "Activation de votre compte"

            # Version HTML du mail
            html_message = render_to_string('emails/activation_email.html', {
                'user': user,
                'activation_link': activation_link,
            })

            # Version texte simple
            plain_message = (
                f"Bonjour {user.username},\n\n"
                f"Merci de vous être inscrit sur notre site.\n"
                f"Pour activer votre compte, cliquez sur ce lien : {activation_link}\n\n"
                f"Si vous n'avez pas demandé cette inscription, ignorez cet email.\n\n"
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
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'number': user.number,
                    'birthdate': user.birthdate,
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivateAccountView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Lien invalide'}, status=400)

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({'message': 'Compte activé avec succès'})
        else:
            return Response({'error': 'Token invalide ou expiré'}, status=400)


