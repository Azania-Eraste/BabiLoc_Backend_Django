from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reservation.models import Bien, Type_Bien, Tarif, Avis, Reservation, Typetarif
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Créer des annonces de test avec avis pour BabiLoc'

    def handle(self, *args, **options):
        self.stdout.write("🏠 Création d'annonces de test réalistes...")
        
        # Vérifier les biens existants
        biens_existants = Bien.objects.all()
        self.stdout.write(f"📋 Biens actuels: {biens_existants.count()}")
        
        for bien in biens_existants:
            avis_count = bien.avis.count()
            tarifs = bien.tarifs.all()
            prix_info = f"{tarifs.first().prix} FCFA" if tarifs.exists() else "Pas de tarif"
            
            self.stdout.write(f"  🏠 {bien.nom}")
            self.stdout.write(f"     🆔 ID: {bien.id}")
            self.stdout.write(f"     💰 Prix: {prix_info}")
            self.stdout.write(f"     ⭐ Avis: {avis_count}")
            self.stdout.write(f"     ✅ Disponible: {bien.disponibility}")
            
        # Si moins de 3 biens, en créer d'autres
        if biens_existants.count() < 3:
            self.stdout.write("\n➕ Création de biens supplémentaires...")
            self._creer_biens_supplementaires()
        
        # Créer des avis pour les biens sans avis
        self._creer_avis_manquants()
        
        # Afficher le résumé final
        self._afficher_resume()

    def _creer_biens_supplementaires(self):
        """Créer des biens supplémentaires si nécessaire"""
        
        # Récupérer des utilisateurs existants
        try:
            proprietaire = User.objects.filter(is_staff=False).first()
            if not proprietaire:
                self.stdout.write("⚠️  Aucun utilisateur trouvé pour créer des biens")
                return
        except Exception as e:
            self.stdout.write(f"❌ Erreur utilisateur: {e}")
            return
        
        # Récupérer ou créer un type de bien
        type_bien, created = Type_Bien.objects.get_or_create(
            nom='Villa',
            defaults={'description': 'Villa de luxe'}
        )
        
        # Données des nouveaux biens
        nouveaux_biens = [
            {
                'nom': 'Villa Moderne Cocody Premium',
                'description': 'Superbe villa 4 chambres avec piscine, jardin tropical et sécurité 24h/24. Quartier résidentiel calme et prestigieux.',
                'prix': 95000
            },
            {
                'nom': 'Appartement Standing Plateau',
                'description': 'Appartement 3 pièces haut standing au cœur du Plateau business. Vue panoramique, parking sécurisé.',
                'prix': 55000
            }
        ]
        
        for bien_data in nouveaux_biens:
            prix = bien_data.pop('prix')
            
            bien, created = Bien.objects.get_or_create(
                nom=bien_data['nom'],
                defaults={
                    **bien_data,
                    'owner': proprietaire,
                    'type_bien': type_bien,
                    'noteGlobale': 0.0,
                    'vues': 0,
                    'disponibility': True,
                }
            )
            
            if created:
                self.stdout.write(f"✅ Bien créé: {bien.nom}")
                
                # Créer le tarif
                tarif, created = Tarif.objects.get_or_create(
                    bien=bien,
                    type_tarif=Typetarif.JOURNALIER.name,
                    defaults={'prix': float(prix)}
                )
                
                if created:
                    self.stdout.write(f"   💰 Tarif: {prix} FCFA/jour")

    def _creer_avis_manquants(self):
        """Créer des avis pour les biens qui n'en ont pas"""
        
        try:
            # Récupérer un client pour créer les avis
            client = User.objects.filter(is_staff=False).exclude(
                id__in=Bien.objects.values_list('owner_id', flat=True)
            ).first()
            
            if not client:
                # Créer un client de test
                client = User.objects.create_user(
                    username=f'client_avis_{timezone.now().strftime("%Y%m%d")}',
                    email='client.avis@test.com',
                    password='testpass123'
                )
                self.stdout.write(f"✅ Client créé: {client.username}")
            
            # Pour chaque bien sans avis suffisants
            biens_sans_avis = Bien.objects.filter(avis__isnull=True).distinct()
            
            for bien in biens_sans_avis[:3]:  # Maximum 3 biens
                self.stdout.write(f"⭐ Création d'avis pour: {bien.nom}")
                
                # Créer une réservation terminée
                date_debut = timezone.now() - timedelta(days=10)
                date_fin = timezone.now() - timedelta(days=5)
                
                reservation, created = Reservation.objects.get_or_create(
                    user=client,
                    bien=bien,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    defaults={
                        'status': 'completed',
                        'prix_total': Decimal('250000'),
                        'type_tarif': 'JOURNALIER',
                        'message': f'Réservation test pour avis {bien.nom}'
                    }
                )
                
                if created:
                    self.stdout.write(f"   📅 Réservation créée")
                
                # Créer l'avis
                avis_data = self._generer_avis_aleatoire()
                
                avis, created = Avis.objects.get_or_create(
                    reservation=reservation,
                    defaults={
                        'user': client,
                        'bien': bien,
                        **avis_data
                    }
                )
                
                if created:
                    self.stdout.write(f"   ⭐ Avis créé: {avis.note}/5 étoiles")
                    
                    # Mettre à jour la note globale
                    bien.noteGlobale = avis.note
                    bien.save()
                    
        except Exception as e:
            self.stdout.write(f"❌ Erreur création avis: {e}")

    def _generer_avis_aleatoire(self):
        """Générer des données d'avis réalistes"""
        import random
        
        commentaires = [
            "Excellent séjour ! Tout était parfait, je recommande vivement cette location.",
            "Très bon bien, propre et bien équipé. Le propriétaire est très réactif.",
            "Parfait pour notre séjour en famille. Emplacement idéal et confortable.",
            "Bonne expérience dans l'ensemble. Quelques petits détails à améliorer mais satisfait.",
            "Superbe découverte ! Nous reviendrons certainement lors de notre prochain voyage."
        ]
        
        note = random.choice([4, 5])  # Notes positives pour les tests
        
        return {
            'note': note,
            'commentaire': random.choice(commentaires),
            'note_proprete': random.choice([4, 5]),
            'note_communication': random.choice([4, 5]),
            'note_emplacement': random.choice([4, 5]),
            'note_rapport_qualite_prix': random.choice([4, 5]),
            'recommande': True,
        }

    def _afficher_resume(self):
        """Afficher le résumé final"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📱 DONNÉES DISPONIBLES POUR VOTRE APP")
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
            self.stdout.write(f"   ⭐ Note: {note_moyenne} ({avis_count} avis)")
            self.stdout.write(f"   📱 Testable dans l'app")
        
        self.stdout.write(f"\n🎉 Total: {biens.count()} biens disponibles")
        self.stdout.write("\n💡 Vous pouvez maintenant tester les avis dans votre app Flutter !")
