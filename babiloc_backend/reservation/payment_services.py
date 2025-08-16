from decimal import Decimal
from django.conf import settings
from django.utils import timezone
# Importer depuis notre implémentation locale
from .cinetpay_sdk.s_d_k import Cinetpay
import uuid
import logging
from .models import Paiement, Reservation, StatutPaiement, TypeOperation, HistoriquePaiement

logger = logging.getLogger(__name__)

class CinetPayService:
    """Service pour gérer les paiements avec CinetPay"""
    
    def __init__(self):
        self.apikey = settings.CINETPAY_API_KEY
        self.site_id = settings.CINETPAY_SITE_ID
        self.secret_key = settings.CINETPAY_SECRET_KEY
        self.client = Cinetpay(self.apikey, self.site_id)

    def generate_transaction_id(self):
        """Générer un ID de transaction unique"""
        return f"BABILOC_{uuid.uuid4().hex[:16].upper()}"
    
    def create_payment(self, reservation_id, return_url=None, notify_url=None):
        """Initialiser un paiement CinetPay"""
        try:
            reservation = Reservation.objects.get(id=reservation_id)
            
            # Vérifier que la réservation peut être payée
            if reservation.status != 'pending':
                return {'error': 'Cette réservation ne peut pas être payée'}
            
            # Générer un ID de transaction unique
            transaction_id = self.generate_transaction_id()
            
            # Créer l'enregistrement de paiement
            paiement = Paiement.objects.create(
                montant=float(reservation.prix_total),
                utilisateur=reservation.user,
                reservation=reservation,
                type_operation=TypeOperation.EN_ATTENTE,
                transaction_id=transaction_id
            )
            
            # Préparer les données pour CinetPay
            payment_data = {
                'amount': int(reservation.prix_total),
                'currency': "XOF",
                'transaction_id': transaction_id,
                'description': f"Paiement réservation #{reservation.id} - {reservation.bien.nom}",
                'return_url': return_url or f"myapp://payment/success/{paiement.id}",
                'notify_url': notify_url or f"{settings.BASE_URL}/api/location/webhooks/cinetpay/",
                'customer_name': reservation.user.first_name or reservation.user.username,
                'customer_surname': reservation.user.last_name or "",
                'customer_email': reservation.user.email,
                'customer_phone_number': getattr(reservation.user, 'number', ''),
            }
            
            # Initialiser le paiement avec CinetPay
            response = self.client.PaymentInitialization(payment_data)
            
            logger.info(f"CinetPay response: {response}")
            
            if response.get('code') == '201':
                # Succès - mettre à jour le paiement avec les infos CinetPay
                paiement.payment_token = response.get('data', {}).get('payment_token')
                paiement.payment_url = response.get('data', {}).get('payment_url')
                paiement.save()
                
                # Enregistrer dans l'historique
                paiement.enregistrer_historique(
                    TypeOperation.INITIALISATION,
                    description=f"Paiement initialisé - Token: {paiement.payment_token}"
                )
                
                return {
                    'success': True,
                    'payment_id': paiement.id,
                    'payment_url': paiement.payment_url,
                    'payment_token': paiement.payment_token,
                    'transaction_id': transaction_id,
                    'amount': float(reservation.prix_total)
                }
            else:
                # Erreur - supprimer le paiement créé
                paiement.delete()
                return {
                    'error': f"Erreur CinetPay: {response.get('message', 'Erreur inconnue')}",
                    'code': response.get('code')
                }
                
        except Reservation.DoesNotExist:
            return {'error': 'Réservation non trouvée'}
        except Exception as e:
            logger.error(f"Erreur lors de la création du paiement: {str(e)}")
            return {'error': f'Erreur interne: {str(e)}'}
    
    def check_payment_status(self, transaction_id):
        """Vérifier le statut d'un paiement"""
        try:
            # Try different possible method names for payment status check
            if hasattr(self.client, 'PaymentCheck'):
                response = self.client.PaymentCheck({'transaction_id': transaction_id})
            elif hasattr(self.client, 'checkPayment'):
                response = self.client.checkPayment({'transaction_id': transaction_id})
            elif hasattr(self.client, 'getPaymentStatus'):
                response = self.client.getPaymentStatus({'transaction_id': transaction_id})
            elif hasattr(self.client, 'PaymentStatus'):
                response = self.client.PaymentStatus({'transaction_id': transaction_id})
            else:
                # Fallback: try to get payment info from database
                try:
                    paiement = Paiement.objects.get(transaction_id=transaction_id)
                    return {
                        'code': '00' if paiement.statut_paiement == StatutPaiement.EFFECTUE else '01',
                        'message': 'Paiement vérifié depuis la base de données',
                        'data': {
                            'transaction_id': transaction_id,
                            'status': paiement.statut_paiement,
                            'amount': paiement.montant
                        }
                    }
                except Paiement.DoesNotExist:
                    return {'error': 'Transaction non trouvée'}
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du paiement: {str(e)}")
            return {'error': str(e)}
    
    def confirm_payment(self, transaction_id, cinetpay_transaction_id=None):
        """Confirmer un paiement après notification"""
        try:
            paiement = Paiement.objects.get(transaction_id=transaction_id)
            
            # Vérifier le statut auprès de CinetPay
            status_response = self.check_payment_status(transaction_id)
            
            # Check if payment is successful
            is_successful = (
                status_response.get('code') == '00' or 
                status_response.get('status') == 'ACCEPTED' or
                status_response.get('data', {}).get('status') == 'ACCEPTED'
            )
            
            if is_successful:
                # Mettre à jour le paiement
                paiement.statut_paiement = StatutPaiement.EFFECTUE
                paiement.cinetpay_transaction_id = cinetpay_transaction_id
                paiement.date_paiement = timezone.now()
                paiement.save()
                
                # Mettre à jour la réservation
                reservation = paiement.reservation
                reservation.status = 'confirmed'
                reservation.save()
                
                # Créer les enregistrements de revenus
                self._creer_enregistrements_revenus(reservation, paiement)
                
                # Enregistrer dans l'historique
                paiement.enregistrer_historique(
                    TypeOperation.RESERVATION,
                    description=f"Paiement confirmé - CinetPay ID: {cinetpay_transaction_id}"
                )
                
                return {
                    'success': True,
                    'message': 'Paiement confirmé avec succès',
                    'reservation_id': reservation.id,
                    'repartition': {
                        'proprietaire': float(reservation.revenu_proprietaire),
                        'plateforme': float(reservation.commission_plateforme)
                    }
                }
            else:
                return {
                    'error': 'Paiement non confirmé par CinetPay',
                    'status': status_response
                }
                
        except Paiement.DoesNotExist:
            return {'error': 'Paiement non trouvé'}
        except Exception as e:
            logger.error(f"Erreur lors de la confirmation du paiement: {str(e)}")
            return {'error': str(e)}
    
    def cancel_payment(self, transaction_id, reason="Annulé par l'utilisateur"):
        """Annuler un paiement"""
        try:
            paiement = Paiement.objects.get(transaction_id=transaction_id)
            paiement.statut_paiement = StatutPaiement.ANNULE
            paiement.save()
            
            # Enregistrer dans l'historique
            paiement.enregistrer_historique(
                TypeOperation.ANNULATION,
                description=f"Paiement annulé: {reason}"
            )
            
            return {'success': True, 'message': 'Paiement annulé'}
        except Paiement.DoesNotExist:
            return {'error': 'Paiement non trouvé'}
        except Exception as e:
            return {'error': str(e)}

    def _creer_enregistrements_revenus(self, reservation, paiement):
        """Créer les enregistrements de revenus pour le propriétaire et la plateforme"""
        
        # Enregistrement pour le propriétaire (85%)
        HistoriquePaiement.objects.create(
            paiement=paiement,
            utilisateur=reservation.bien.owner,  # Le propriétaire du bien
            type_operation=TypeOperation.RESERVATION,
            montant=float(reservation.revenu_proprietaire),
            description=f"Revenu propriétaire (85%) - Réservation #{reservation.id}"
        )
        
        # Enregistrement pour la plateforme (15%)
        HistoriquePaiement.objects.create(
            paiement=paiement,
            utilisateur=None,  # Pas d'utilisateur spécifique pour la plateforme
            type_operation=TypeOperation.COMMISSION,
            montant=float(reservation.commission_plateforme),
            description=f"Commission plateforme (15%) - Réservation #{reservation.id}"
        )

# Instance globale du service
cinetpay_service = CinetPayService()