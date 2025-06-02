from .models import CustomUser
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import RegisterSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import generate_activation_link
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

class RegisterView(APIView):
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


