# Auths/utils.py
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_activation_link(user, request):
    from django.urls import reverse
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_url = request.build_absolute_uri(
        reverse('activate', kwargs={'uidb64': uid, 'token': token})
    )
    return activation_url

def bien_image_upload_to(instance, filename):
    """
    Retourne un chemin Cloudinary du style:
      biens/<bien_slug_ou_id>/<filename>
    - Si l'instance a un FK 'bien' => utilise son slug ou id
    - Sinon, tente d'utiliser slug/id de l'instance
    """
    bien = getattr(instance, 'bien', None)
    if bien is not None:
        key = getattr(bien, 'slug', None) or getattr(bien, 'id', None) or 'unknown'
    else:
        key = getattr(instance, 'slug', None) or getattr(instance, 'id', None) or 'unknown'
    return f"biens/{key}/{filename}"
