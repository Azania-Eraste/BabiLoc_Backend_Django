#!/usr/bin/env python
"""
Script pour vérifier les avis dans la base de données
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

def verifier_avis():
    """Vérifie les avis dans la base de données"""
    print("=== AVIS DANS LA BDD ===")
    avis = Avis.objects.all()
    print(f"Nombre d'avis: {avis.count()}")
    
    for a in avis:
        print(f"Avis {a.id}:")
        print(f"  - Auteur: {a.user.username} (ID: {a.user.id})")
        print(f"  - Bien: {a.bien.id}")
        print(f"  - Note: {a.note}")
        print(f"  - Note globale: {getattr(a, 'note_globale', 'N/A')}")
        print(f"  - Commentaire: {a.commentaire}")
        print(f"  - Date: {a.created_at}")
        print()

if __name__ == "__main__":
    verifier_avis()
