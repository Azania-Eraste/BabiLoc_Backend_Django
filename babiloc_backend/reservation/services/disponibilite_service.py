"""
Service de gestion automatique de la disponibilité des véhicules
Met à jour la disponibilité en fonction des réservations
"""
from django.utils import timezone
from datetime import datetime, timedelta
from reservation.models import Reservation, Bien
import logging

logger = logging.getLogger(__name__)


class DisponibiliteService:
    """Service centralisé pour la gestion de la disponibilité des véhicules"""
    
    @staticmethod
    def mettre_a_jour_disponibilite_vehicule(bien):
        """
        Met à jour la disponibilité d'un véhicule en fonction de ses réservations
        """
        try:
            maintenant = timezone.now()
            
            # Vérifier s'il y a des réservations actives ou futures
            reservations_actives = Reservation.objects.filter(
                bien=bien,
                status__in=['confirmee', 'en_cours'],
                date_fin__gte=maintenant
            ).exists()
            
            # Vérifier s'il y a des réservations en cours
            reservations_en_cours = Reservation.objects.filter(
                bien=bien,
                status='en_cours',
                date_debut__lte=maintenant,
                date_fin__gte=maintenant
            ).exists()
            
            # Déterminer la nouvelle disponibilité
            if reservations_en_cours:
                nouvelle_disponibilite = False
                nouveau_statut = 'en_cours'
            elif reservations_actives:
                nouvelle_disponibilite = False
                nouveau_statut = 'reserve'
            else:
                nouvelle_disponibilite = True
                nouveau_statut = 'disponible'
            
            # Mettre à jour si nécessaire
            if bien.disponibility != nouvelle_disponibilite or bien.status != nouveau_statut:
                bien.disponibility = nouvelle_disponibilite
                bien.status = nouveau_statut
                bien.save()
                
                logger.info(f"Disponibilité mise à jour pour véhicule {bien.id}: {nouvelle_disponibilite} ({nouveau_statut})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur mise à jour disponibilité véhicule {bien.id}: {e}")
            return False
    
    @staticmethod
    def mettre_a_jour_disponibilite_apres_reservation(reservation):
        """
        Met à jour la disponibilité après création/modification d'une réservation
        """
        try:
            return DisponibiliteService.mettre_a_jour_disponibilite_vehicule(reservation.bien)
        except Exception as e:
            logger.error(f"Erreur mise à jour disponibilité après réservation {reservation.id}: {e}")
            return False
    
    @staticmethod
    def mettre_a_jour_disponibilite_apres_annulation(reservation):
        """
        Met à jour la disponibilité après annulation d'une réservation
        """
        try:
            # Marquer la réservation comme annulée si ce n'est pas déjà fait
            if reservation.status != 'annulee':
                reservation.status = 'annulee'
                reservation.save()
            
            # Mettre à jour la disponibilité du véhicule
            return DisponibiliteService.mettre_a_jour_disponibilite_vehicule(reservation.bien)
            
        except Exception as e:
            logger.error(f"Erreur mise à jour disponibilité après annulation {reservation.id}: {e}")
            return False
    
    @staticmethod
    def verifier_disponibilite_periode(bien, date_debut, date_fin, reservation_exclue=None):
        """
        Vérifie si un véhicule est disponible pour une période donnée
        """
        try:
            # Construire la requête de base
            query = Reservation.objects.filter(
                bien=bien,
                status__in=['confirmee', 'en_cours'],
            )
            
            # Exclure une réservation spécifique (utile pour les modifications)
            if reservation_exclue:
                query = query.exclude(id=reservation_exclue.id)
            
            # Vérifier les conflits de dates
            conflits = query.filter(
                # Début de la nouvelle réservation pendant une réservation existante
                date_debut__lte=date_debut,
                date_fin__gt=date_debut
            ) | query.filter(
                # Fin de la nouvelle réservation pendant une réservation existante
                date_debut__lt=date_fin,
                date_fin__gte=date_fin
            ) | query.filter(
                # Nouvelle réservation englobe une réservation existante
                date_debut__gte=date_debut,
                date_fin__lte=date_fin
            )
            
            disponible = not conflits.exists()
            
            logger.info(f"Vérification disponibilité véhicule {bien.id} du {date_debut} au {date_fin}: {disponible}")
            return disponible
            
        except Exception as e:
            logger.error(f"Erreur vérification disponibilité véhicule {bien.id}: {e}")
            return False
    
    @staticmethod
    def obtenir_dates_indisponibles(bien, mois=None, annee=None):
        """
        Obtient la liste des dates indisponibles pour un véhicule
        """
        try:
            # Si pas de mois/année spécifiés, prendre le mois courant
            if mois is None or annee is None:
                maintenant = timezone.now()
                mois = maintenant.month
                annee = maintenant.year
            
            # Calculer le début et la fin du mois
            debut_mois = datetime(annee, mois, 1)
            if mois == 12:
                fin_mois = datetime(annee + 1, 1, 1) - timedelta(days=1)
            else:
                fin_mois = datetime(annee, mois + 1, 1) - timedelta(days=1)
            
            # Récupérer les réservations pour ce mois
            reservations = Reservation.objects.filter(
                bien=bien,
                status__in=['confirmee', 'en_cours'],
                date_debut__lte=fin_mois,
                date_fin__gte=debut_mois
            )
            
            # Construire la liste des dates indisponibles
            dates_indisponibles = []
            for reservation in reservations:
                date_courante = max(reservation.date_debut.date(), debut_mois.date())
                date_fin = min(reservation.date_fin.date(), fin_mois.date())
                
                while date_courante <= date_fin:
                    dates_indisponibles.append(date_courante.isoformat())
                    date_courante += timedelta(days=1)
            
            logger.info(f"Dates indisponibles pour véhicule {bien.id} en {mois}/{annee}: {len(dates_indisponibles)} jours")
            return list(set(dates_indisponibles))  # Supprimer les doublons
            
        except Exception as e:
            logger.error(f"Erreur obtention dates indisponibles véhicule {bien.id}: {e}")
            return []
    
    @staticmethod
    def mettre_a_jour_statuts_reservations():
        """
        Met à jour automatiquement les statuts des réservations selon les dates
        (À exécuter via une tâche cron)
        """
        try:
            maintenant = timezone.now()
            reservations_modifiees = 0
            
            # Marquer comme "en_cours" les réservations confirmées qui ont commencé
            reservations_a_demarrer = Reservation.objects.filter(
                status='confirmee',
                date_debut__lte=maintenant,
                date_fin__gt=maintenant
            )
            
            for reservation in reservations_a_demarrer:
                reservation.status = 'en_cours'
                reservation.save()
                reservations_modifiees += 1
                logger.info(f"Réservation {reservation.id} marquée comme 'en_cours'")
            
            # Marquer comme "terminee" les réservations en cours qui sont finies
            reservations_a_terminer = Reservation.objects.filter(
                status='en_cours',
                date_fin__lte=maintenant
            )
            
            for reservation in reservations_a_terminer:
                reservation.status = 'terminee'
                reservation.save()
                reservations_modifiees += 1
                logger.info(f"Réservation {reservation.id} marquée comme 'terminee'")
            
            # Mettre à jour la disponibilité de tous les véhicules concernés
            vehicules_concernes = set()
            for reservation in list(reservations_a_demarrer) + list(reservations_a_terminer):
                vehicules_concernes.add(reservation.bien)
            
            for vehicule in vehicules_concernes:
                DisponibiliteService.mettre_a_jour_disponibilite_vehicule(vehicule)
            
            logger.info(f"Mise à jour automatique terminée: {reservations_modifiees} réservations modifiées, {len(vehicules_concernes)} véhicules mis à jour")
            return reservations_modifiees
            
        except Exception as e:
            logger.error(f"Erreur mise à jour automatique des statuts: {e}")
            return 0
