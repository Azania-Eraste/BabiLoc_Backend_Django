"""
Service de notifications pour les réservations
Gère l'envoi d'emails automatiques pour toutes les étapes de réservation
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service centralisé pour toutes les notifications de réservation"""
    
    @staticmethod
    def envoyer_notification_nouvelle_reservation(reservation):
        """
        Envoie une notification au propriétaire quand une nouvelle réservation est créée
        """
        try:
            # Email au propriétaire
            proprietaire_email = reservation.bien.proprietaire.email
            client_nom = f"{reservation.user.first_name} {reservation.user.last_name}"
            
            subject = f"🎉 Nouvelle réservation pour {reservation.bien.nom}"
            
            # Contexte pour le template
            context = {
                'proprietaire_nom': reservation.bien.proprietaire.first_name,
                'client_nom': client_nom,
                'client_email': reservation.user.email,
                'client_telephone': getattr(reservation.user, 'telephone', 'Non renseigné'),
                'bien_nom': reservation.bien.nom,
                'date_debut': reservation.date_debut,
                'date_fin': reservation.date_fin,
                'prix_total': reservation.prix_total,
                'statut': reservation.get_status_display(),
                'url_gestion': f"{settings.FRONTEND_URL}/gestion/reservations",
                'date_creation': reservation.created_at,
            }
            
            # Rendu du template HTML
            html_content = render_to_string(
                'emails/proprietaire_nouvelle_reservation.html',
                context
            )
            text_content = render_to_string(
                'emails/proprietaire_nouvelle_reservation.txt',
                context
            )
            
            # Envoi de l'email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[proprietaire_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Notification nouvelle réservation envoyée au propriétaire {proprietaire_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi notification nouvelle réservation: {e}")
            return False
    
    @staticmethod
    def envoyer_confirmation_reservation_client(reservation):
        """
        Envoie une confirmation de réservation au client
        """
        try:
            client_email = reservation.user.email
            client_nom = f"{reservation.user.first_name} {reservation.user.last_name}"
            
            subject = f"✅ Confirmation de votre réservation - {reservation.bien.nom}"
            
            context = {
                'client_nom': client_nom,
                'bien_nom': reservation.bien.nom,
                'proprietaire_nom': f"{reservation.bien.proprietaire.first_name} {reservation.bien.proprietaire.last_name}",
                'proprietaire_telephone': getattr(reservation.bien.proprietaire, 'telephone', 'Non renseigné'),
                'date_debut': reservation.date_debut,
                'date_fin': reservation.date_fin,
                'prix_total': reservation.prix_total,
                'statut': reservation.get_status_display(),
                'numero_reservation': reservation.id,
                'url_reservations': f"{settings.FRONTEND_URL}/mes-reservations",
                'date_creation': reservation.created_at,
                'lieu_recuperation': getattr(reservation.bien, 'adresse', 'À convenir avec le propriétaire'),
            }
            
            html_content = render_to_string(
                'emails/client_confirmation_reservation.html',
                context
            )
            text_content = render_to_string(
                'emails/client_confirmation_reservation.txt',
                context
            )
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[client_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Confirmation réservation envoyée au client {client_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi confirmation client: {e}")
            return False
    
    @staticmethod
    def envoyer_notification_changement_statut(reservation, ancien_statut, nouveau_statut):
        """
        Envoie une notification quand le statut de la réservation change
        """
        try:
            # Messages selon le changement de statut
            messages_statut = {
                ('en_attente', 'confirmee'): {
                    'client_subject': '✅ Votre réservation a été confirmée !',
                    'client_message': 'Bonne nouvelle ! Le propriétaire a confirmé votre réservation.',
                    'proprietaire_subject': '✅ Réservation confirmée',
                    'proprietaire_message': 'Vous avez confirmé la réservation.',
                },
                ('en_attente', 'annulee'): {
                    'client_subject': '❌ Réservation annulée',
                    'client_message': 'Votre réservation a été annulée par le propriétaire.',
                    'proprietaire_subject': '❌ Réservation annulée',
                    'proprietaire_message': 'Vous avez annulé la réservation.',
                },
                ('confirmee', 'en_cours'): {
                    'client_subject': '🚗 Votre location commence !',
                    'client_message': 'Votre période de location a commencé. Profitez bien !',
                    'proprietaire_subject': '🚗 Location en cours',
                    'proprietaire_message': 'La période de location a commencé.',
                },
                ('en_cours', 'terminee'): {
                    'client_subject': '🏁 Location terminée - Merci !',
                    'client_message': 'Votre location est terminée. Merci d\'avoir utilisé BabiLoc !',
                    'proprietaire_subject': '🏁 Location terminée',
                    'proprietaire_message': 'La location est terminée.',
                },
            }
            
            # Récupérer les messages pour ce changement de statut
            cle_changement = (ancien_statut, nouveau_statut)
            if cle_changement not in messages_statut:
                logger.warning(f"Pas de template pour le changement {ancien_statut} -> {nouveau_statut}")
                return False
            
            messages = messages_statut[cle_changement]
            
            # Envoi au client
            NotificationService._envoyer_email_changement_statut(
                reservation=reservation,
                destinataire=reservation.user,
                subject=messages['client_subject'],
                message_personnalise=messages['client_message'],
                type_destinataire='client'
            )
            
            # Envoi au propriétaire
            NotificationService._envoyer_email_changement_statut(
                reservation=reservation,
                destinataire=reservation.bien.proprietaire,
                subject=messages['proprietaire_subject'],
                message_personnalise=messages['proprietaire_message'],
                type_destinataire='proprietaire'
            )
            
            logger.info(f"Notifications changement statut envoyées pour réservation {reservation.id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi notification changement statut: {e}")
            return False
    
    @staticmethod
    def _envoyer_email_changement_statut(reservation, destinataire, subject, message_personnalise, type_destinataire):
        """
        Envoie un email de changement de statut à un destinataire spécifique
        """
        try:
            context = {
                'destinataire_nom': destinataire.first_name,
                'bien_nom': reservation.bien.nom,
                'date_debut': reservation.date_debut,
                'date_fin': reservation.date_fin,
                'prix_total': reservation.prix_total,
                'nouveau_statut': reservation.get_status_display(),
                'numero_reservation': reservation.id,
                'message_personnalise': message_personnalise,
                'url_dashboard': f"{settings.FRONTEND_URL}/dashboard",
                'type_destinataire': type_destinataire,
            }
            
            html_content = render_to_string(
                'emails/changement_statut_reservation.html',
                context
            )
            text_content = render_to_string(
                'emails/changement_statut_reservation.txt',
                context
            )
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinataire.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email changement statut: {e}")
            return False
    
    @staticmethod
    def envoyer_notification_annulation(reservation, annule_par):
        """
        Envoie une notification d'annulation à toutes les parties concernées
        """
        try:
            # Déterminer qui a annulé et adapter les messages
            if annule_par == 'client':
                # Client a annulé -> notifier le propriétaire
                NotificationService._envoyer_email_annulation_proprietaire(reservation)
                NotificationService._envoyer_email_annulation_confirmation_client(reservation)
            elif annule_par == 'proprietaire':
                # Propriétaire a annulé -> notifier le client
                NotificationService._envoyer_email_annulation_client(reservation)
                NotificationService._envoyer_email_annulation_confirmation_proprietaire(reservation)
            
            logger.info(f"Notifications annulation envoyées pour réservation {reservation.id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi notification annulation: {e}")
            return False
    
    @staticmethod
    def _envoyer_email_annulation_proprietaire(reservation):
        """Email au propriétaire quand le client annule"""
        subject = f"❌ Annulation de réservation - {reservation.bien.nom}"
        
        context = {
            'proprietaire_nom': reservation.bien.proprietaire.first_name,
            'client_nom': f"{reservation.user.first_name} {reservation.user.last_name}",
            'bien_nom': reservation.bien.nom,
            'date_debut': reservation.date_debut,
            'date_fin': reservation.date_fin,
            'prix_total': reservation.prix_total,
            'numero_reservation': reservation.id,
            'date_annulation': timezone.now(),
            'annule_par': 'client',
        }
        
        html_content = render_to_string('emails/annulation_proprietaire.html', context)
        text_content = render_to_string('emails/annulation_proprietaire.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reservation.bien.proprietaire.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    
    @staticmethod
    def _envoyer_email_annulation_client(reservation):
        """Email au client quand le propriétaire annule"""
        subject = f"❌ Annulation de votre réservation - {reservation.bien.nom}"
        
        context = {
            'client_nom': reservation.user.first_name,
            'proprietaire_nom': f"{reservation.bien.proprietaire.first_name} {reservation.bien.proprietaire.last_name}",
            'bien_nom': reservation.bien.nom,
            'date_debut': reservation.date_debut,
            'date_fin': reservation.date_fin,
            'prix_total': reservation.prix_total,
            'numero_reservation': reservation.id,
            'date_annulation': timezone.now(),
            'annule_par': 'proprietaire',
            'url_support': f"{settings.FRONTEND_URL}/support",
        }
        
        html_content = render_to_string('emails/annulation_client.html', context)
        text_content = render_to_string('emails/annulation_client.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reservation.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    
    @staticmethod
    def _envoyer_email_annulation_confirmation_client(reservation):
        """Email de confirmation d'annulation au client"""
        subject = f"✅ Confirmation d'annulation - {reservation.bien.nom}"
        
        context = {
            'client_nom': reservation.user.first_name,
            'bien_nom': reservation.bien.nom,
            'numero_reservation': reservation.id,
            'date_annulation': timezone.now(),
        }
        
        html_content = render_to_string('emails/confirmation_annulation_client.html', context)
        text_content = render_to_string('emails/confirmation_annulation_client.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reservation.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    
    @staticmethod
    def _envoyer_email_annulation_confirmation_proprietaire(reservation):
        """Email de confirmation d'annulation au propriétaire"""
        subject = f"✅ Confirmation d'annulation - {reservation.bien.nom}"
        
        context = {
            'proprietaire_nom': reservation.bien.proprietaire.first_name,
            'bien_nom': reservation.bien.nom,
            'numero_reservation': reservation.id,
            'date_annulation': timezone.now(),
        }
        
        html_content = render_to_string('emails/confirmation_annulation_proprietaire.html', context)
        text_content = render_to_string('emails/confirmation_annulation_proprietaire.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reservation.bien.proprietaire.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
