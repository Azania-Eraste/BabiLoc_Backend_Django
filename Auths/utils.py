# Auths/utils.py
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from django.utils.text import slugify

def generate_activation_link(user, request):
    from django.urls import reverse
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_url = request.build_absolute_uri(
        reverse('activate', kwargs={'uidb64': uid, 'token': token})
    )
    return activation_url

def bien_image_upload_to(instance, filename):
    bien = getattr(instance, 'bien', None)
    key = (getattr(bien, 'slug', None) if bien else None) or \
          (getattr(bien, 'id', None) if bien else None) or \
          getattr(instance, 'slug', None) or getattr(instance, 'id', None) or 'unknown'
    return f"biens/{key}/{filename}"

def document_upload_to(instance, filename):
    """
    documents/<userID>_<username>/<type_document>/<filename>
    """
    user = getattr(instance, 'utilisateur', None)
    type_doc = getattr(instance, 'type_document', 'autre')
    if user:
        base = f"{user.id}_{slugify(getattr(user, 'username', '') or 'user')}"
    else:
        base = "inconnu"
    return f"documents/{base}/{type_doc}/{filename}"
