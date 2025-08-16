#!/usr/bin/env python
"""
Script pour supprimer tous les avis de la base de données
Usage: python delete_all_avis.py
"""

import os
import sys
import django

# Ajouter le chemin du projet Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'babiloc_backend.settings')
django.setup()

from reservation.models import Avis

def delete_all_avis():
    """Supprime tous les avis de la base de données"""
    try:
        # Compter le nombre d'avis avant suppression
        count_before = Avis.objects.count()
        print(f"🔍 Nombre d'avis avant suppression : {count_before}")
        
        if count_before == 0:
            print("✅ Aucun avis à supprimer")
            return
        
        # Supprimer tous les avis
        deleted_count, _ = Avis.objects.all().delete()
        
        print(f"🗑️ {deleted_count} avis supprimés avec succès")
        
        # Vérification
        count_after = Avis.objects.count()
        print(f"✅ Nombre d'avis après suppression : {count_after}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la suppression : {e}")

if __name__ == "__main__":
    print("🚀 Début de la suppression des avis...")
    delete_all_avis()
    print("✅ Script terminé")
