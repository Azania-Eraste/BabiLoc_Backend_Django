from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

# ✅ Nettoyage des imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models
from django.http import HttpResponse, Http404

from django.shortcuts import get_object_or_404
from .models import Reservation, HistoriqueStatutReservation, RevenuProprietaire
from rest_framework.views import APIView
from django.db.models import Sum, F, Q
from Auths import permission
from .serializers import (
    ReservationSerializer, 
    ReservationCreateSerializer, 
    ReservationUpdateSerializer,
    ReservationListSerializer,
)
from decimal import Decimal

logger = logging.getLogger(__name__)

class ReservationDetailView(generics.RetrieveUpdateAPIView):
    """Détails et mise à jour d'une réservation"""
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(
            Q(user=user) | Q(bien__owner=user)
        ).select_related('user', 'bien')

class SoldeHoteView(APIView):
    """Vue pour afficher le solde du propriétaire (hôte)"""
    permission_classes = [permission.IsVendor]
    
    @swagger_auto_schema(
        operation_description="Récupérer le solde et les revenus du propriétaire",
        responses={
            200: openapi.Response(
                description="Solde récupéré avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'revenus_bruts_total': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'commission_plateforme': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'revenus_nets_proprietaire': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'pourcentage_commission': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'pourcentage_proprietaire': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            401: "Non authentifié",
            403: "Permission refusée"
        },
        tags=['Hôte', 'Revenus']
    )
    def get(self, request):
        proprietaire = request.user
        
        # Récupérer toutes les réservations complétées pour les biens du propriétaire
        reservations_completees = Reservation.objects.filter(
            bien__owner=proprietaire,
            status='completed'
        )
        
        total_revenus_bruts = sum(r.prix_total for r in reservations_completees)
        commission_totale = sum(r.commission_plateforme for r in reservations_completees)
        revenus_nets_proprietaire = sum(r.revenu_proprietaire for r in reservations_completees)
        
        return Response({
            "revenus_bruts_total": float(total_revenus_bruts),
            "commission_plateforme": float(commission_totale),
            "revenus_nets_proprietaire": float(revenus_nets_proprietaire),
            "pourcentage_commission": 15,
            "pourcentage_proprietaire": 85
        })

class HistoriqueRevenusProprietaireView(APIView):
    """Historique des revenus pour un propriétaire"""
    permission_classes = [permission.IsVendor]
    
    @swagger_auto_schema(
        operation_description="Récupérer l'historique des revenus du propriétaire",
        responses={
            200: "Historique récupéré avec succès",
            401: "Non authentifié",
            403: "Permission refusée"
        },
        tags=['Hôte', 'Revenus']
    )
    def get(self, request):
        proprietaire = request.user
        
        revenus = RevenuProprietaire.objects.filter(
            proprietaire=proprietaire
        ).select_related('reservation', 'reservation__bien').order_by('-date_creation')
        
        revenus_data = []
        for revenu in revenus:
            revenus_data.append({
                'id': revenu.id,
                'reservation_id': revenu.reservation.id,
                'bien_nom': revenu.reservation.bien.nom,
                'montant_brut': float(revenu.montant_brut),
                'commission_plateforme': float(revenu.commission_plateforme),
                'revenu_net': float(revenu.revenu_net),
                'status_paiement': revenu.status_paiement,
                'date_creation': revenu.date_creation,
                'date_versement': revenu.date_versement
            })
        
        return Response(revenus_data)

@swagger_auto_schema(
    method='get',
    operation_description="Vérifier si l'utilisateur peut accéder au chat de cette réservation",
    responses={
        200: openapi.Response(
            description="Statut d'accès au chat",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'peut_chatter': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'statut': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        403: "Accès refusé",
        404: "Réservation non trouvée"
    },
    tags=['Réservations', 'Chat']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def verifier_acces_chat(request, reservation_id):
    """
    Vérifier si l'utilisateur peut accéder au chat pour cette réservation.
    Le chat n'est accessible que si la réservation est confirmée ou terminée.
    """
    try:
        reservation = Reservation.objects.select_related('user', 'bien__owner').get(id=reservation_id)
        
        # Vérifier que l'utilisateur est concerné (client OU hôte)
        if request.user != reservation.user and request.user != reservation.bien.owner:
            return Response({
                'success': False,
                'peut_chatter': False,
                'message': 'Vous n\'avez pas accès à cette réservation'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Le chat est accessible si la réservation est confirmée ou terminée
        peut_chatter = reservation.status in ['confirmed', 'completed']
        
        message = 'Chat accessible' if peut_chatter else 'La réservation doit être confirmée par l\'hôte avant de pouvoir discuter'
        
        return Response({
            'success': True,
            'peut_chatter': peut_chatter,
            'statut': reservation.status,
            'message': message
        }, status=status.HTTP_200_OK)
        
    except Reservation.DoesNotExist:
        return Response({
            'success': False,
            'peut_chatter': False,
            'error': 'Réservation non trouvée'
        }, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='post',
    operation_description="Confirmer une réservation en attente (hôte uniquement)",
    responses={
        200: openapi.Response(
            description="Réservation confirmée avec succès",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'reservation': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: "Statut invalide",
        403: "Seul l'hôte peut confirmer",
        404: "Réservation non trouvée"
    },
    tags=['Hôte', 'Réservations']
)
@api_view(['POST'])
@permission_classes([permission.IsVendor])
def confirmer_reservation_hote(request, reservation_id):
    """
    Permet à l'hôte de confirmer une réservation en attente.
    Une fois confirmée, le chat devient accessible pour les deux parties.
    """
    try:
        reservation = Reservation.objects.select_related('user', 'bien__owner').get(id=reservation_id)
        
        # Vérifier que l'utilisateur connecté est bien l'hôte
        if request.user != reservation.bien.owner:
            return Response({
                'success': False,
                'error': 'Seul le propriétaire du bien peut confirmer cette réservation'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier que la réservation est en attente
        if reservation.status != 'pending':
            return Response({
                'success': False,
                'error': f'Cette réservation ne peut pas être confirmée (statut actuel: {reservation.get_status_display()})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Confirmer la réservation
        reservation.status = 'confirmed'
        reservation.confirmed_at = timezone.now()
        reservation.save()
        
        logger.info(f"Réservation {reservation_id} confirmée par l'hôte {request.user.id}")
        
        # Envoyer notification au client (optionnel)
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            send_mail(
                subject=f'Réservation confirmée - {reservation.bien.nom}',
                message=f'Bonjour {reservation.user.get_full_name() or reservation.user.username},\n\nVotre réservation pour "{reservation.bien.nom}" a été confirmée par l\'hôte.\nVous pouvez maintenant discuter avec votre hôte via le chat.\n\nDétails:\n- Date de début: {reservation.date_debut}\n- Date de fin: {reservation.date_fin}\n- Montant: {reservation.prix_total} FCFA',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[reservation.user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.warning(f"Erreur lors de l'envoi de l'email de confirmation: {str(e)}")
        
        return Response({
            'success': True,
            'message': 'Réservation confirmée avec succès',
            'reservation': ReservationSerializer(reservation).data
        }, status=status.HTTP_200_OK)
        
    except Reservation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Réservation non trouvée'
        }, status=status.HTTP_404_NOT_FOUND)
