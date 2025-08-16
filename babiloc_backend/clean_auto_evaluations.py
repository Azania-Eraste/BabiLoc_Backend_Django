#!/usr/bin/env python
"""
Script pour nettoyer les auto-évaluations dans la base de données
Un utilisateur ne devrait jamais pouvoir évaluer ses propres biens
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'babiloc_backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from reservation.models import Avis
from django.db.models import Q, F

def nettoyer_auto_evaluations():
    """
    Supprime tous les avis où l'utilisateur a évalué ses propres biens
    """
    print("🔍 Recherche des auto-évaluations...")
    
    # Trouver tous les avis où l'utilisateur évalue ses propres biens
    auto_evaluations = Avis.objects.filter(
        user__id=F('bien__owner__id')  # L'ID utilisateur de l'avis = ID propriétaire du bien
    )
    
    nombre_auto_evaluations = auto_evaluations.count()
    
    if nombre_auto_evaluations == 0:
        print("✅ Aucune auto-évaluation trouvée. Base de données propre.")
        return
    
    print(f"⚠️ {nombre_auto_evaluations} auto-évaluation(s) trouvée(s) :")
    
    for avis in auto_evaluations:
        print(f"  - Avis {avis.id}: {avis.user.username} a évalué son propre bien '{avis.bien.nom}' avec {avis.note}/5")
    
    # Demander confirmation
    confirmation = input(f"\n❓ Voulez-vous supprimer ces {nombre_auto_evaluations} auto-évaluation(s) ? (oui/non): ")
    
    if confirmation.lower() in ['oui', 'o', 'yes', 'y']:
        # Supprimer les auto-évaluations
        auto_evaluations.delete()
        print(f"✅ {nombre_auto_evaluations} auto-évaluation(s) supprimée(s) avec succès.")
        print("🎯 Le système est maintenant conforme : seuls les locataires peuvent évaluer les propriétaires.")
    else:
        print("❌ Suppression annulée.")

def afficher_statistiques():
    """
    Affiche les statistiques des avis après nettoyage
    """
    print("\n📊 STATISTIQUES APRÈS NETTOYAGE :")
    
    total_avis = Avis.objects.count()
    print(f"  - Total des avis valides : {total_avis}")
    
    if total_avis > 0:
        # Grouper par utilisateur
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        for user in User.objects.all():
            avis_donnes = Avis.objects.filter(user=user).count()
            avis_recus = Avis.objects.filter(bien__owner=user).exclude(user=user).count()
            
            if avis_donnes > 0 or avis_recus > 0:
                print(f"  - {user.username}: {avis_donnes} avis donnés, {avis_recus} avis reçus")
    else:
        print("  💡 Aucun avis dans le système. Créez un deuxième compte pour tester les évaluations.")

if __name__ == "__main__":
    print("🧹 NETTOYAGE DES AUTO-ÉVALUATIONS")
    print("="*50)
    
    nettoyer_auto_evaluations()
    afficher_statistiques()
    
    print("\n✨ Nettoyage terminé.")
    print("💡 Prochaines étapes :")
    print("   1. Créer un deuxième compte utilisateur")
    print("   2. Faire une réservation d'un bien de Franck avec le nouveau compte")
    print("   3. Terminer la réservation")
    print("   4. Évaluer le bien en tant que locataire")
