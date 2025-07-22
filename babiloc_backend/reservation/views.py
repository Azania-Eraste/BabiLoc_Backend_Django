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
