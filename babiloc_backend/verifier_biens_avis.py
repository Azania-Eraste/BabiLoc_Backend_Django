#!/usr/bin/env python
"""
Script pour vérifier les propriétaires des biens
"""

import os
import sys
import django

# Ajouter le chemin du projet Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'babiloc_backend.settings')
django.setup()

from reservation.models import Bien, Avis

def verifier_biens_et_avis():
    """Vérifie les biens et leurs propriétaires"""
    print("=== BIENS ET PROPRIÉTAIRES ===")
    biens = Bien.objects.all()
    for bien in biens:
        print(f"Bien {bien.id}: {bien.nom}")
        print(f"  - Propriétaire: {bien.owner.username} (ID: {bien.owner.id})")
        
        # Vérifier les avis sur ce bien
        avis_bien = Avis.objects.filter(bien=bien)
        print(f"  - Avis sur ce bien: {avis_bien.count()}")
        for avis in avis_bien:
            print(f"    * Avis de {avis.user.username} (ID: {avis.user.id}): {avis.note}/5")
        print()

if __name__ == "__main__":
    verifier_biens_et_avis()
