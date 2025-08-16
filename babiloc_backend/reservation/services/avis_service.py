"""
Service pour gérer les avis et notations après les réservations
"""

from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Q
from django.utils import timezone
from ..models import Avis, Reservation, Bien
from django.contrib.auth import get_user_model

User = get_user_model()

class AvisService:
    """Service centralisé pour la gestion des avis et notations"""
    
    @staticmethod
    def peut_donner_avis(user, reservation_id):
        """
        Vérifie si un utilisateur peut donner un avis pour une réservation ET un bien.
        Un utilisateur ne peut donner qu'un seul avis par bien.
        """
        try:
            reservation = Reservation.objects.get(id=reservation_id)
        except Reservation.DoesNotExist:
            return False, "Réservation introuvable"
        
        # Vérifications de sécurité
        if reservation.user != user:
            return False, "Cette réservation ne vous appartient pas"
        
        # EMPÊCHER L'AUTO-ÉVALUATION : Un utilisateur ne peut pas évaluer ses propres biens
        if reservation.bien.owner == user:
            return False, "Vous ne pouvez pas évaluer vos propres biens"
        
        if reservation.status != 'completed':
            return False, "La réservation doit être terminée pour donner un avis"
        
        # *** Logique modifiée ici pour vérifier l'avis par bien et utilisateur ***
        if Avis.objects.filter(user=user, bien=reservation.bien).exists():
            return False, "Vous avez déjà donné un avis pour ce bien."
        
        return True, "Peut donner un avis"
    
    @staticmethod
    def creer_avis(user, reservation_id, donnees_avis):
        """
        Crée un avis après validation
        """
        peut_donner, message = AvisService.peut_donner_avis(user, reservation_id)
        if not peut_donner:
            raise ValidationError(message)
        
        reservation = Reservation.objects.get(id=reservation_id)
        
        # Créer l'avis avec validation automatique
        avis = Avis.objects.create(
            user=user,
            bien=reservation.bien,
            reservation=reservation,
            note=donnees_avis.get('note'),
            commentaire=donnees_avis.get('commentaire', ''),
            note_proprete=donnees_avis.get('note_proprete'),
            note_communication=donnees_avis.get('note_communication'),
            note_emplacement=donnees_avis.get('note_emplacement'),
            note_rapport_qualite_prix=donnees_avis.get('note_rapport_qualite_prix'),
            recommande=donnees_avis.get('recommande', True)
        )
        
        return avis
    
    @staticmethod
    def obtenir_reservations_sans_avis(user):
        """
        Retourne les réservations terminées pour lesquelles l'utilisateur n'a pas encore donné d'avis
        """
        reservations_terminees = Reservation.objects.filter(
            user=user,
            status='completed'
        ).exclude(
            id__in=Avis.objects.filter(user=user).values_list('reservation_id', flat=True)
        )
        
        return reservations_terminees
    
    @staticmethod
    def calculer_statistiques_bien(bien_id):
        """
        Calcule les statistiques détaillées d'un bien
        """
        avis_bien = Avis.objects.filter(bien_id=bien_id, est_valide=True)
        
        if not avis_bien.exists():
            return {
                'note_moyenne': 0,
                'nombre_avis': 0,
                'repartition_notes': {},
                'notes_detaillees': {}
            }
        
        stats = avis_bien.aggregate(
            note_moyenne=Avg('note'),
            note_proprete_moy=Avg('note_proprete'),
            note_communication_moy=Avg('note_communication'),
            note_emplacement_moy=Avg('note_emplacement'),
            note_qualite_prix_moy=Avg('note_rapport_qualite_prix'),
            nombre_avis=Count('id')
        )
        
        # Répartition des notes (1-5 étoiles)
        repartition = {}
        for i in range(1, 6):
            repartition[f"{i}_etoiles"] = avis_bien.filter(note=i).count()
        
        return {
            'note_moyenne': round(stats['note_moyenne'], 1) if stats['note_moyenne'] else 0,
            'nombre_avis': stats['nombre_avis'],
            'repartition_notes': repartition,
            'notes_detaillees': {
                'proprete': round(stats['note_proprete_moy'], 1) if stats['note_proprete_moy'] else None,
                'communication': round(stats['note_communication_moy'], 1) if stats['note_communication_moy'] else None,
                'emplacement': round(stats['note_emplacement_moy'], 1) if stats['note_emplacement_moy'] else None,
                'qualite_prix': round(stats['note_qualite_prix_moy'], 1) if stats['note_qualite_prix_moy'] else None,
            },
            'pourcentage_recommandation': round(
                (avis_bien.filter(recommande=True).count() / stats['nombre_avis']) * 100, 1
            ) if stats['nombre_avis'] > 0 else 0
        }
    
    @staticmethod
    def obtenir_avis_utilisateur(user_id):
        """
        Obtient les statistiques d'avis pour un utilisateur (en tant que propriétaire)
        EXCLUT LES AUTO-ÉVALUATIONS pour un système réaliste
        """
        # Avis reçus sur ses biens (EXCLUANT les auto-évaluations)
        avis_recus = Avis.objects.filter(
            bien__owner_id=user_id,
            est_valide=True
        ).exclude(
            user_id=user_id  # EXCLURE les avis que l'utilisateur s'est donné à lui-même
        )
        
        if not avis_recus.exists():
            return {
                'nombre_avis': 0,
                'moyenne_globale': 0.0,
                'moyenne_proprete': 0.0,
                'moyenne_communication': 0.0,
                'moyenne_emplacement': 0.0,
                'moyenne_qualite_prix': 0.0,
                'note_moyenne_proprietaire': 0,
                'nombre_avis_recus': 0,
                'avis_recents': []
            }
        
        # Calculer toutes les moyennes
        stats = avis_recus.aggregate(
            note_moyenne=Avg('note'),
            moyenne_proprete=Avg('note_proprete'),
            moyenne_communication=Avg('note_communication'),
            moyenne_emplacement=Avg('note_emplacement'),
            moyenne_qualite_prix=Avg('note_rapport_qualite_prix'),
            nombre_avis=Count('id')
        )
        
        # Utiliser la note globale comme fallback si les notes détaillées sont manquantes
        note_fallback = stats['note_moyenne'] if stats['note_moyenne'] else 0.0
        
        avis_recents = avis_recus.select_related('user', 'bien').order_by('-created_at')[:5]
        
        return {
            'nombre_avis': stats['nombre_avis'],
            'moyenne_globale': round(stats['note_moyenne'], 1) if stats['note_moyenne'] else 0.0,
            'moyenne_proprete': round(stats['moyenne_proprete'], 1) if stats['moyenne_proprete'] else round(note_fallback, 1),
            'moyenne_communication': round(stats['moyenne_communication'], 1) if stats['moyenne_communication'] else round(note_fallback, 1),
            'moyenne_emplacement': round(stats['moyenne_emplacement'], 1) if stats['moyenne_emplacement'] else round(note_fallback, 1),
            'moyenne_qualite_prix': round(stats['moyenne_qualite_prix'], 1) if stats['moyenne_qualite_prix'] else round(note_fallback, 1),
            'note_moyenne_proprietaire': round(stats['note_moyenne'], 1) if stats['note_moyenne'] else 0,
            'nombre_avis_recus': stats['nombre_avis'],
            'avis_recents': [
                {
                    'id': avis.id,
                    'note': avis.note,
                    'commentaire': avis.commentaire[:100] + '...' if len(avis.commentaire) > 100 else avis.commentaire,
                    'bien_nom': avis.bien.nom,
                    'utilisateur': avis.user.username,
                    'date': avis.created_at
                }
                for avis in avis_recents
            ]
        }
    
    @staticmethod
    def peut_repondre_avis(user, avis_id):
        """
        Vérifie si un utilisateur peut répondre à un avis
        """
        try:
            avis = Avis.objects.get(id=avis_id)
        except Avis.DoesNotExist:
            return False, "Avis introuvable"
        
        # Seul le propriétaire du bien peut répondre
        if avis.bien.owner != user:
            return False, "Seul le propriétaire peut répondre à cet avis"
        
        # Vérifier qu'une réponse n'existe pas déjà
        if avis.reponse_proprietaire:
            return False, "Vous avez déjà répondu à cet avis"
        
        return True, "Peut répondre"
    
    @staticmethod
    def repondre_avis(user, avis_id, reponse):
        """
        Ajoute une réponse du propriétaire à un avis
        """
        peut_repondre, message = AvisService.peut_repondre_avis(user, avis_id)
        if not peut_repondre:
            raise ValidationError(message)
        
        avis = Avis.objects.get(id=avis_id)
        avis.reponse_proprietaire = reponse
        avis.date_reponse = timezone.now()
        avis.save()
        
        return avis
