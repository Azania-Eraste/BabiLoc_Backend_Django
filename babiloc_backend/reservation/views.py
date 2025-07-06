from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .payment_services import cinetpay_service
import json
import logging

# ✅ Add missing imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models  # ✅ Add this import
from django.http import HttpResponse, Http404

from django.shortcuts import get_object_or_404
from .models import Reservation, Paiement, HistoriquePaiement, TypeOperation, Facture
from rest_framework.views import APIView
from django.db.models import Sum, F, Q  # ✅ Add Q import
from Auths import permission
from .serializers import (
    ReservationSerializer, 
    ReservationCreateSerializer, 
    ReservationUpdateSerializer,
    ReservationListSerializer,
    HistoriquePaiementSerializer,
    FactureSerializer, FactureCreateSerializer
)
from decimal import Decimal

logger = logging.getLogger(__name__)

# ✅ Ajouter les vues manquantes
class ReservationDetailView(generics.RetrieveUpdateAPIView):
    """Détails et mise à jour d'une réservation"""
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
        if not self.request.user.is_authenticated:
            return Reservation.objects.none()
            
        if self.request.user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return ReservationUpdateSerializer
        return ReservationSerializer

class HistoriquePaiementsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        paiements = Paiement.objects.filter(utilisateur=request.user).order_by('-created_at')
        serializer = HistoriquePaiementSerializer(paiements, many=True)
        return Response(serializer.data)

class SoldeHoteView(APIView):
    """Vue pour afficher le solde du propriétaire (hôte)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Récupérer toutes les réservations complétées pour les biens de l'utilisateur
        reservations_completees = Reservation.objects.filter(
            bien__owner=user,  # L'utilisateur est propriétaire du bien
            status="completed"  # Réservation terminée
        )

        # Calculer les revenus
        total_revenus_bruts = reservations_completees.aggregate(
            total=Sum('prix_total')
        )['total'] or Decimal("0")
        
        # Commission de la plateforme (15%)
        commission_totale = total_revenus_bruts * Decimal("0.15")
        
        # Revenus nets du propriétaire (85%)
        revenus_nets_proprietaire = total_revenus_bruts * Decimal("0.85")

        return Response({
            "nombre_reservations": reservations_completees.count(),
            "revenus_bruts_total": float(total_revenus_bruts),
            "commission_plateforme": float(commission_totale),
            "revenus_nets_proprietaire": float(revenus_nets_proprietaire),
            "pourcentage_commission": 15,
            "pourcentage_proprietaire": 85
        })

class CreateReservationView(generics.CreateAPIView):
    serializer_class = ReservationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MesReservationsView(generics.ListAPIView):
    serializer_class = ReservationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
        if not self.request.user.is_authenticated:
            return Reservation.objects.none()
            
        return Reservation.objects.filter(user=self.request.user)

class AllReservationsView(generics.ListAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationListSerializer
    permission_classes = [permissions.IsAdminUser]

class CreatePaymentView(APIView):
    """Créer un paiement CinetPay"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Initialiser un paiement avec CinetPay",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["reservation_id"],
            properties={
                'reservation_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID de la réservation à payer"
                ),
                'return_url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="URL de retour après paiement (optionnel)"
                ),
                'notify_url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="URL de notification (optionnel)"
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="Paiement initialisé",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'payment_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'payment_url': openapi.Schema(type=openapi.TYPE_STRING),
                        'transaction_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                    }
                )
            ),
            400: "Erreur dans les données"
        },
        tags=['Paiements']
    )
    def post(self, request):
        reservation_id = request.data.get('reservation_id')
        return_url = request.data.get('return_url')
        notify_url = request.data.get('notify_url')
        
        if not reservation_id:
            return Response({'error': 'reservation_id requis'}, status=400)
        
        result = cinetpay_service.create_payment(
            reservation_id=reservation_id,
            return_url=return_url,
            notify_url=notify_url
        )
        
        if 'error' in result:
            return Response(result, status=400)
        
        return Response(result)

class PaymentStatusView(APIView):
    """Vérifier le statut d'un paiement"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Vérifier le statut d'un paiement",
        manual_parameters=[
            openapi.Parameter(
                'transaction_id',
                openapi.IN_QUERY,
                description="ID de transaction",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        tags=['Paiements']
    )
    def get(self, request):
        transaction_id = request.query_params.get('transaction_id')
        
        if not transaction_id:
            return Response({'error': 'transaction_id requis'}, status=400)
        
        result = cinetpay_service.check_payment_status(transaction_id)
        return Response(result)

@method_decorator(csrf_exempt, name='dispatch')
class CinetPayWebhookView(APIView):
    """Webhook pour les notifications CinetPay"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            # Log de la requête reçue
            logger.info(f"CinetPay webhook reçu: {request.body}")
            
            data = json.loads(request.body) if request.body else request.data
            
            transaction_id = data.get('cpm_trans_id')  # ID de votre transaction
            cinetpay_transaction_id = data.get('cpm_trans_id')  # ID CinetPay
            status = data.get('cpm_result')
            
            if status == '00':  # Paiement réussi
                result = cinetpay_service.confirm_payment(
                    transaction_id=transaction_id,
                    cinetpay_transaction_id=cinetpay_transaction_id
                )
                
                if result.get('success'):
                    logger.info(f"Paiement confirmé: {transaction_id}")
                    return Response({'status': 'success'})
                else:
                    logger.error(f"Erreur confirmation paiement: {result}")
                    return Response({'status': 'error', 'message': result.get('error')})
            else:
                # Paiement échoué
                cinetpay_service.cancel_payment(
                    transaction_id=transaction_id,
                    reason=f"Paiement échoué - Code: {status}"
                )
                logger.info(f"Paiement échoué: {transaction_id} - Code: {status}")
                return Response({'status': 'failed'})
                
        except Exception as e:
            logger.error(f"Erreur webhook CinetPay: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=400)

# Fonction utilitaire pour les tests
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_payment(request):
    """Annuler un paiement"""
    transaction_id = request.data.get('transaction_id')
    reason = request.data.get('reason', 'Annulé par l\'utilisateur')
    
    if not transaction_id:
        return Response({'error': 'transaction_id requis'}, status=400)
    
    result = cinetpay_service.cancel_payment(transaction_id, reason)
    
    if 'error' in result:
        return Response(result, status=400)
    
    return Response(result)

class HistoriqueRevenusProprietaireView(APIView):
    """Historique des revenus pour un propriétaire"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Historique des revenus du propriétaire",
        responses={200: "Liste des revenus"},
        tags=['Propriétaire', 'Revenus']
    )
    def get(self, request):
        # ✅ Add protection for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response([])
        
        from .models import RevenuProprietaire
        
        # Récupérer les revenus du propriétaire connecté
        revenus = RevenuProprietaire.objects.filter(
            proprietaire=request.user,
            status_paiement='verse'
        ).select_related('reservation', 'reservation__bien')
        
        data = []
        for revenu in revenus:
            reservation = revenu.reservation
            data.append({
                'id': revenu.id,
                'reservation_id': reservation.id,
                'bien_nom': reservation.bien.nom,
                'montant_revenu': float(revenu.revenu_net),
                'date_paiement': revenu.created_at,
                'montant_total_reservation': float(reservation.prix_total),
                'commission_plateforme': float(reservation.commission_plateforme)
            })
        
        return Response({
            'revenus': data,
            'total_revenus': sum(item['montant_revenu'] for item in data)
        })

class FactureListView(generics.ListAPIView):
    """Liste des factures pour l'utilisateur connecté"""
    serializer_class = FactureSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer la liste de mes factures",
        responses={
            200: FactureSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Factures']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        # ✅ Add protection for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Facture.objects.none()
        
        user = self.request.user
        return Facture.objects.filter(
            Q(reservation__user=user) | 
            Q(reservation__bien__owner=user)
        ).order_by('-date_emission')

class FactureDetailView(generics.RetrieveAPIView):
    """Détails d'une facture"""
    serializer_class = FactureSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Add protection for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Facture.objects.none()
        
        user = self.request.user
        return Facture.objects.filter(
            Q(reservation__user=user) | 
            Q(reservation__bien__owner=user)
        )
    
    @swagger_auto_schema(
        operation_description="Détails d'une facture",
        responses={
            200: FactureSerializer,
            401: "Non authentifié",
            404: "Facture non trouvée"
        },
        tags=['Factures']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class FactureCreateView(generics.CreateAPIView):
    """Créer une facture manuellement"""
    serializer_class = FactureCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Créer une facture",
        request_body=FactureCreateSerializer,
        responses={
            201: FactureSerializer,
            400: "Données invalides",
            401: "Non authentifié"
        },
        tags=['Factures']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        facture = serializer.save()
        # Envoyer automatiquement par email
        facture.envoyer_par_email()

class FactureDownloadView(APIView):
    """Télécharger le PDF d'une facture"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Télécharger le PDF d'une facture",
        responses={
            200: "Fichier PDF",
            401: "Non authentifié",
            404: "Facture non trouvée"
        },
        tags=['Factures']
    )
    def get(self, request, pk):
        try:
            facture = Facture.objects.get(
                pk=pk,
                reservation__user=request.user
            )
        except Facture.DoesNotExist:
            # Vérifier si l'utilisateur est le propriétaire
            try:
                facture = Facture.objects.get(
                    pk=pk,
                    reservation__bien__owner=request.user
                )
            except Facture.DoesNotExist:
                raise Http404("Facture non trouvée")
        
        if not facture.fichier_pdf:
            # Générer le PDF s'il n'existe pas
            facture.generer_pdf()
            facture.refresh_from_db()
        
        if facture.fichier_pdf:
            response = HttpResponse(
                facture.fichier_pdf.read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="facture_{facture.numero_facture}.pdf"'
            return response
        
        return Response({'error': 'Fichier PDF non disponible'}, status=404)

class FactureResendEmailView(APIView):
    """Renvoyer une facture par email"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Renvoyer une facture par email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="Email de destination (optionnel)"
                )
            }
        ),
        responses={
            200: "Email envoyé",
            400: "Erreur d'envoi",
            401: "Non authentifié",
            404: "Facture non trouvée"
        },
        tags=['Factures']
    )
    def post(self, request, pk):
        try:
            facture = Facture.objects.get(
                pk=pk,
                reservation__user=request.user
            )
        except Facture.DoesNotExist:
            # Vérifier si l'utilisateur est le propriétaire
            try:
                facture = Facture.objects.get(
                    pk=pk,
                    reservation__bien__owner=request.user
                )
            except Facture.DoesNotExist:
                return Response({'error': 'Facture non trouvée'}, status=404)
        
        email_destination = request.data.get('email')
        
        if facture.envoyer_par_email(destinataire_email=email_destination):
            return Response({'message': 'Facture envoyée par email avec succès'})
        else:
            return Response({'error': 'Erreur lors de l\'envoi de l\'email'}, status=400)

# Vue pour les hôtes - Factures reçues
class FacturesHoteView(generics.ListAPIView):
    """Liste des factures pour les biens de l'hôte"""
    serializer_class = FactureSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer les factures de mes biens (hôte)",
        responses={
            200: FactureSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Factures', 'Hôte']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        # ✅ Add protection for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Facture.objects.none()
        
        return Facture.objects.filter(
            reservation__bien__owner=self.request.user
        ).order_by('-date_emission')
