from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from .payment_services import cinetpay_service
import json
import logging

# ✅ Add missing imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models  # ✅ Add this import
from django.http import HttpResponse, Http404

from django.shortcuts import get_object_or_404
from .models import Reservation, Paiement, HistoriquePaiement, TypeOperation, Facture, Bien
from rest_framework.views import APIView
from django.db.models import Sum, F, Q  # ✅ Add Q import
from Auths import permission
from .serializers import (
    ReservationSerializer, 
    ReservationCreateSerializer, 
    ReservationUpdateSerializer,
    ReservationListSerializer,
    HistoriquePaiementSerializer,
    FactureSerializer, FactureCreateSerializer,
    ChoicesSerializer
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
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Retourner les données avec l'ID de la réservation
        response_data = serializer.data
        response_data['id'] = serializer.instance.id
        response_data['success'] = True
        response_data['message'] = 'Réservation créée avec succès'
        
        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

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

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_reservation(request):
    """Annuler une réservation."""
    reservation_id = request.data.get('reservation_id')

    if not reservation_id:
        return Response({'error': 'L\'ID de réservation est requis.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Réservation non trouvée.'}, status=status.HTTP_404_NOT_FOUND)

    # Vérifier les permissions: Seul l'utilisateur qui a fait la réservation ou un admin peut annuler
    if not (request.user == reservation.user or request.user.is_staff):
        return Response({'error': 'Vous n\'avez pas la permission d\'annuler cette réservation.'}, status=status.HTTP_403_FORBIDDEN)

    # Empêcher l'annulation si la réservation est déjà terminée ou annulée
    if reservation.status == 'completed':
        return Response({'error': 'Une réservation terminée ne peut pas être annulée.'}, status=status.HTTP_400_BAD_REQUEST)
    if reservation.status == 'cancelled':
        return Response({'error': 'Cette réservation est déjà annulée.'}, status=status.HTTP_400_BAD_REQUEST)

    # Annuler la réservation
    reservation.status = 'cancelled'
    reservation.save()

    logger.info(f"Réservation {reservation_id} annulée par {request.user.username}")
    return Response({'success': True, 'message': 'Réservation annulée avec succès.'}, status=status.HTTP_200_OK)

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


# ==========================================
# ✅ NOUVELLES VUES POUR LA DISPONIBILITÉ
# ==========================================

from .services.disponibilite_service import DisponibiliteService
from .models import Bien
from datetime import datetime

@api_view(['GET'])
def obtenir_disponibilite_vehicule(request, bien_id):
    """
    Obtient la disponibilité d'un véhicule pour un mois donné
    """
    try:
        bien = get_object_or_404(Bien, id=bien_id)
        
        # Récupérer les paramètres de date
        mois = request.GET.get('mois')
        annee = request.GET.get('annee')
        
        if mois:
            mois = int(mois)
        if annee:
            annee = int(annee)
        
        # Obtenir les dates indisponibles
        dates_indisponibles = DisponibiliteService.obtenir_dates_indisponibles(
            bien, mois, annee
        )
        
        return Response({
            'success': True,
            'data': {
                'vehicule_id': bien.id,
                'vehicule_nom': bien.nom,
                'disponibilite_generale': bien.disponibility,
                'statut': bien.status,
                'dates_indisponibles': dates_indisponibles,
                'mois': mois or timezone.now().month,
                'annee': annee or timezone.now().year,
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur obtention disponibilité véhicule {bien_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def verifier_disponibilite_periode(request, bien_id):
    """
    Vérifie si un véhicule est disponible pour une période donnée
    """
    try:
        bien = get_object_or_404(Bien, id=bien_id)
        
        # Récupérer les données
        date_debut_str = request.data.get('date_debut')
        date_fin_str = request.data.get('date_fin')
        reservation_id = request.data.get('reservation_id')  # Pour exclure une réservation existante
        
        if not date_debut_str or not date_fin_str:
            return Response({
                'success': False,
                'error': 'Les dates de début et de fin sont requises'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convertir les dates
        try:
            date_debut = datetime.fromisoformat(date_debut_str.replace('Z', '+00:00'))
            date_fin = datetime.fromisoformat(date_fin_str.replace('Z', '+00:00'))
        except ValueError:
            return Response({
                'success': False,
                'error': 'Format de date invalide. Utilisez le format ISO 8601'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier que la date de début est antérieure à la date de fin
        if date_debut >= date_fin:
            return Response({
                'success': False,
                'error': 'La date de début doit être antérieure à la date de fin'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer la réservation à exclure si spécifiée
        reservation_exclue = None
        if reservation_id:
            try:
                reservation_exclue = Reservation.objects.get(id=reservation_id)
            except Reservation.DoesNotExist:
                pass
        
        # Vérifier la disponibilité
        disponible = DisponibiliteService.verifier_disponibilite_periode(
            bien, date_debut, date_fin, reservation_exclue
        )
        
        return Response({
            'success': True,
            'data': {
                'vehicule_id': bien.id,
                'vehicule_nom': bien.nom,
                'date_debut': date_debut.isoformat(),
                'date_fin': date_fin.isoformat(),
                'disponible': disponible,
                'message': 'Véhicule disponible pour cette période' if disponible else 'Véhicule non disponible pour cette période'
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur vérification disponibilité véhicule {bien_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def forcer_mise_a_jour_disponibilite(request, bien_id):
    """
    Force la mise à jour de la disponibilité d'un véhicule
    (Fonction d'administration)
    """
    try:
        bien = get_object_or_404(Bien, id=bien_id)
        
        # Vérifier que l'utilisateur est le propriétaire ou un admin
        if not (request.user.is_staff or bien.proprietaire == request.user):
            return Response({
                'success': False,
                'error': 'Vous n\'avez pas l\'autorisation de modifier ce véhicule'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Forcer la mise à jour
        mise_a_jour_effectuee = DisponibiliteService.mettre_a_jour_disponibilite_vehicule(bien)
        
        # Recharger le véhicule pour obtenir les dernières données
        bien.refresh_from_db()
        
        return Response({
            'success': True,
            'data': {
                'vehicule_id': bien.id,
                'vehicule_nom': bien.nom,
                'nouvelle_disponibilite': bien.disponibility,
                'nouveau_statut': bien.status,
                'mise_a_jour_effectuee': mise_a_jour_effectuee,
                'message': 'Disponibilité mise à jour avec succès'
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur force mise à jour disponibilité véhicule {bien_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mettre_a_jour_statuts_automatique(request):
    """
    Lance la mise à jour automatique des statuts de réservation
    (Fonction d'administration)
    """
    try:
        # Vérifier que l'utilisateur est un admin
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Seuls les administrateurs peuvent lancer cette opération'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Lancer la mise à jour automatique
        reservations_modifiees = DisponibiliteService.mettre_a_jour_statuts_reservations()
        
        return Response({
            'success': True,
            'data': {
                'reservations_modifiees': reservations_modifiees,
                'message': f'{reservations_modifiees} réservations ont été mises à jour'
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur mise à jour automatique des statuts: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reservations_bien(request):
    """
    Récupère les réservations existantes d'un bien spécifique pour afficher la disponibilité
    
    Query Parameters:
    - bien_id: ID du bien (obligatoire)
    - statut: Statut des réservations à récupérer (optionnel, défaut: 'confirmed')
    
    Utilisé par l'application mobile pour afficher les périodes réservées sur la page de booking
    """
    try:
        # Récupération des paramètres
        bien_id = request.GET.get('bien_id')
        statut = request.GET.get('statut', 'confirmed')
        
        if not bien_id:
            return Response({
                'success': False,
                'error': 'Le paramètre bien_id est obligatoire'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            bien_id = int(bien_id)
        except ValueError:
            return Response({
                'success': False,
                'error': 'Le bien_id doit être un nombre entier'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier que le bien existe
        try:
            bien = Bien.objects.get(id=bien_id)
        except Bien.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Aucun bien trouvé avec l\'ID {bien_id}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Récupérer les réservations selon le statut demandé
        reservations_query = Reservation.objects.filter(bien_id=bien_id)
        
        if statut == 'confirmed':
            # Récupérer uniquement les réservations confirmées
            reservations_query = reservations_query.filter(status='confirmed')
        elif statut == 'all':
            # Récupérer toutes les réservations sauf annulées
            reservations_query = reservations_query.exclude(status='cancelled')
        else:
            # Filtrer par statut spécifique
            reservations_query = reservations_query.filter(status=statut)
        
        # Ordonner par date de début
        reservations = reservations_query.select_related('user').order_by('date_debut')
        
        # Sérialiser les données pour la réponse
        reservations_data = []
        for reservation in reservations:
            reservations_data.append({
                'id': reservation.id,
                'date_debut': reservation.date_debut.strftime('%Y-%m-%d'),
                'date_fin': reservation.date_fin.strftime('%Y-%m-%d'),
                'statut': reservation.status,
                'utilisateur_nom': f"{reservation.user.first_name} {reservation.user.last_name}".strip() or reservation.user.username,
                'prix_total': float(reservation.prix_total),
                'created_at': reservation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        logger.info(f"Réservations bien {bien_id}: {len(reservations_data)} trouvées (statut: {statut})")
        
        return Response({
            'success': True,
            'reservations': reservations_data,
            'count': len(reservations_data),
            'bien_info': {
                'id': bien.id,
                'titre': bien.nom,  # Utiliser 'nom' au lieu de 'titre'
                'proprietaire': f"{bien.owner.first_name} {bien.owner.last_name}".strip() or bien.owner.username,  # Utiliser 'owner' au lieu de 'proprietaire'
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération réservations bien: {e}")
        return Response({
            'success': False,
            'error': f'Erreur interne du serveur: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_reservation_payment(request):
    """Confirmer une réservation après paiement réussi"""
    try:
        reservation_id = request.data.get('reservation_id')
        payment_method = request.data.get('payment_method', 'Mobile Money')
        transaction_id = request.data.get('transaction_id')
        
        if not reservation_id:
            return Response({
                'success': False,
                'error': 'ID de réservation requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer la réservation
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
        
        # Vérifier que la réservation est en attente
        if reservation.status != 'pending':
            return Response({
                'success': False,
                'error': f'Cette réservation a déjà le statut: {reservation.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Confirmer la réservation
        reservation.status = 'confirmed'
        reservation.confirmed_at = timezone.now()
        reservation.save()
        
        # Log pour traçabilité
        logger.info(f"Réservation {reservation_id} confirmée par paiement - Utilisateur: {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Réservation confirmée avec succès',
            'data': {
                'reservation_id': reservation.id,
                'status': reservation.status,
                'confirmed_at': reservation.confirmed_at,
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erreur confirmation réservation: {e}")
        return Response({
            'success': False,
            'error': f'Erreur lors de la confirmation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChoicesView(APIView):
    """Vue pour récupérer les choices de l'application"""
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Récupérer tous les choices (carburant, transmission, etc.)",
        responses={
            200: openapi.Response(
                description="Choices récupérés avec succès",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'carburant': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                        'transmission': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                    }
                )
            )
        },
        tags=['Choices']
    )
    def get(self, request):
        """Récupérer tous les choices disponibles"""
        try:
            choices_data = ChoicesSerializer.get_all_choices()
            return Response({
                'success': True,
                'data': choices_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erreur récupération choices: {e}")
            return Response({
                'success': False,
                'error': f'Erreur lors de la récupération des choices: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
