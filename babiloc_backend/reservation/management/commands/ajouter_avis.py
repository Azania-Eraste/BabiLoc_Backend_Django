from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reservation.models import Bien, Avis, Reservation
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Ajouter des avis aux biens existants'

    def handle(self, *args, **options):
        self.stdout.write("⭐ Ajout d'avis aux biens existants...")
        
        # Récupérer les biens sans avis
        biens_sans_avis = Bien.objects.filter(avis__isnull=True).distinct()
        
        # Récupérer un client pour créer les avis
        client = User.objects.filter(is_staff=False).exclude(
            id__in=Bien.objects.values_list('owner_id', flat=True)
        ).first()
        
        if not client:
            self.stdout.write("❌ Aucun client trouvé")
            return
        
        # Commentaires réalistes
        commentaires_positifs = [
            "Excellent séjour ! Villa impeccable avec une piscine magnifique. Le propriétaire très accueillant et réactif. Je recommande vivement !",
            "Appartement parfait pour notre séjour d'affaires. Très bien situé, propre et tout l'équipement nécessaire. Merci !",
            "Superbe expérience ! Le bien correspond exactement à la description. Quartier calme et sécurisé. Nous reviendrons !",
            "Très satisfait de cette location. Tout était parfait : propreté, emplacement, équipements. Propriétaire très professionnel.",
            "Location au top ! Villa spacieuse, bien équipée et dans un cadre magnifique. Parfait pour des vacances en famille.",
        ]
        
        for bien in biens_sans_avis:
            self.stdout.write(f"📝 Création d'avis pour: {bien.nom}")
            
            # Créer une réservation terminée
            date_debut = timezone.now() - timedelta(days=random.randint(7, 30))
            date_fin = date_debut + timedelta(days=random.randint(3, 7))
            
            try:
                reservation, created = Reservation.objects.get_or_create(
                    user=client,
                    bien=bien,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    defaults={
                        'status': 'completed',
                        'prix_total': Decimal(str(random.randint(200000, 500000))),
                        'type_tarif': 'JOURNALIER',
                        'message': f'Réservation test pour {bien.nom}'
                    }
                )
                
                if created:
                    self.stdout.write(f"   📅 Réservation créée")
                
                # Créer l'avis
                note = random.choice([4, 5])  # Notes positives
                avis, created = Avis.objects.get_or_create(
                    reservation=reservation,
                    defaults={
                        'user': client,
                        'bien': bien,
                        'note': note,
                        'commentaire': random.choice(commentaires_positifs),
                        'note_proprete': random.choice([4, 5]),
                        'note_communication': random.choice([4, 5]),
                        'note_emplacement': random.choice([4, 5]),
                        'note_rapport_qualite_prix': random.choice([4, 5]),
                        'recommande': True,
                    }
                )
                
                if created:
                    self.stdout.write(f"   ⭐ Avis créé: {avis.note}/5 étoiles")
                    
                    # Mettre à jour la note globale
                    bien.noteGlobale = float(avis.note)
                    bien.save()
                else:
                    self.stdout.write(f"   📋 Avis déjà existant")
                    
            except Exception as e:
                self.stdout.write(f"   ❌ Erreur: {e}")
        
        # Afficher le résumé
        self.stdout.write("\n" + "="*50)
        self.stdout.write("🎉 RÉCAPITULATIF DES BIENS AVEC AVIS")
        self.stdout.write("="*50)
        
        biens = Bien.objects.all()
        for bien in biens:
            avis_count = bien.avis.count()
            note_moyenne = bien.noteGlobale if bien.noteGlobale > 0 else "Pas d'avis"
            tarif = bien.tarifs.first()
            prix = f"{tarif.prix:,.0f} FCFA/jour" if tarif else "Prix non défini"
            
            self.stdout.write(f"\n🏠 {bien.nom}")
            self.stdout.write(f"   🆔 ID: {bien.id}")
            self.stdout.write(f"   💰 {prix}")
            self.stdout.write(f"   ⭐ {note_moyenne} ({avis_count} avis)")
            self.stdout.write(f"   📱 Testable dans votre app Flutter")
        
        self.stdout.write(f"\n🚀 Prêt pour les tests ! Utilisez ces IDs dans votre app.")
