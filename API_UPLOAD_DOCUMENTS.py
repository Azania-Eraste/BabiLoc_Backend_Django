"""
API Django pour l'upload de documents de réservation
À ajouter dans reservation/views.py
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.conf import settings
import os
import uuid

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_reservation_documents(request):
    """
    Upload des documents pour une réservation
    """
    try:
        reservation_id = request.data.get('reservation_id')
        if not reservation_id:
            return Response({
                'success': False,
                'error': 'reservation_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier que la réservation appartient à l'utilisateur
        try:
            reservation = Reservation.objects.get(
                id=reservation_id, 
                user=request.user
            )
        except Reservation.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Réservation non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)
        
        uploaded_files = []
        
        # Upload carte d'identité
        if 'carte_identite' in request.FILES:
            carte_identite = request.FILES['carte_identite']
            filename = f"reservations/{reservation_id}/carte_identite_{uuid.uuid4()}{os.path.splitext(carte_identite.name)[1]}"
            saved_path = default_storage.save(filename, carte_identite)
            
            # Sauvegarder le chemin dans le modèle User
            request.user.carte_identite = saved_path
            request.user.save()
            uploaded_files.append('carte_identite')
        
        # Upload permis de conduire (si véhicule)
        if 'permis_conduire' in request.FILES:
            permis = request.FILES['permis_conduire']
            filename = f"reservations/{reservation_id}/permis_{uuid.uuid4()}{os.path.splitext(permis.name)[1]}"
            saved_path = default_storage.save(filename, permis)
            
            request.user.permis_conduire = saved_path
            request.user.save()
            uploaded_files.append('permis_conduire')
        
        # Marquer l'utilisateur comme ayant des documents
        if uploaded_files:
            request.user.est_verifie = True
            request.user.save()
            
            # Optionnel: changer le statut de la réservation
            reservation.status = 'pending'  # En attente de validation des documents
            reservation.save()
        
        return Response({
            'success': True,
            'message': f'Documents uploadés avec succès: {", ".join(uploaded_files)}',
            'uploaded_files': uploaded_files
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# À ajouter dans reservation/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ... autres URLs existantes ...
    path('upload-documents/', views.upload_reservation_documents, name='upload_reservation_documents'),
]
