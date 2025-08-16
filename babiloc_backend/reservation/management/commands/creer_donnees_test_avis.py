"""
Script de test pour créer des données d'exemple et tester le système d'avis
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reservation.models import Bien, Reservation, Avis, Type_Bien
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Crée des données de test pour le système d\'avis'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Création des données de test...')
        
        # 1. Créer des utilisateurs de test
        try:
            client_test = User.objects.get(username='client_test')
        except User.DoesNotExist:
            client_test = User.objects.create_user(
                username='client_test',
                email='client@test.com',
                password='testpass123',
                first_name='John',
                last_name='Doe'
            )
            self.stdout.write('✅ Utilisateur client créé')

        try:
            proprietaire_test = User.objects.get(username='proprietaire_test')
        except User.DoesNotExist:
            proprietaire_test = User.objects.create_user(
                username='proprietaire_test',
                email='proprietaire@test.com',
                password='testpass123',
                first_name='Jane',
                last_name='Smith',
                is_vendor=True
            )
            self.stdout.write('✅ Utilisateur propriétaire créé')

        # 2. Créer un type de bien
        type_bien, created = Type_Bien.objects.get_or_create(
            nom='Villa Test',
            defaults={'description': 'Villa pour les tests'}
        )
        if created:
            self.stdout.write('✅ Type de bien créé')

        # 3. Créer un bien
        bien_test, created = Bien.objects.get_or_create(
            nom='Villa de Test pour Avis',
            defaults={
                'owner': proprietaire_test,
                'type_bien': type_bien,
                'description': 'Belle villa pour tester les avis',
                'noteGlobale': 0.0,
                'vues': 0,
                'disponibility': True,
                # Champs spécifiques véhicule (optionnels)
                'marque': 'Tesla',
                'modele': 'Model S',
                'nb_places': 5,
                'carburant': 'electrique',
                'transmission': 'automatique',
            }
        )
        if created:
            self.stdout.write('✅ Bien de test créé')

        # 3.1. Créer un tarif pour ce bien
        from reservation.models import Typetarif, Tarif
        tarif_test, created = Tarif.objects.get_or_create(
            bien=bien_test,
            type_tarif=Typetarif.JOURNALIER.name,
            defaults={
                'prix': 50000.0,
            }
        )
        if created:
            self.stdout.write('✅ Tarif de test créé')

        # 4. Créer des réservations terminées pour pouvoir donner des avis
        date_debut = timezone.now() - timedelta(days=10)
        date_fin = timezone.now() - timedelta(days=5)
        
        reservation_test, created = Reservation.objects.get_or_create(
            user=client_test,
            bien=bien_test,
            date_debut=date_debut,
            date_fin=date_fin,
            defaults={
                'status': 'completed',  # Réservation terminée
                'prix_total': Decimal('250000'),
                'type_tarif': 'JOURNALIER',
                'message': 'Réservation de test pour avis'
            }
        )
        if created:
            self.stdout.write('✅ Réservation terminée créée')

        # 5. Créer une deuxième réservation sans avis
        date_debut2 = timezone.now() - timedelta(days=20)
        date_fin2 = timezone.now() - timedelta(days=15)
        
        reservation_test2, created = Reservation.objects.get_or_create(
            user=client_test,
            bien=bien_test,
            date_debut=date_debut2,
            date_fin=date_fin2,
            defaults={
                'status': 'completed',
                'prix_total': Decimal('300000'),
                'type_tarif': 'JOURNALIER',
                'message': 'Deuxième réservation de test'
            }
        )
        if created:
            self.stdout.write('✅ Deuxième réservation créée')

        # 6. Créer un avis de test (optionnel)
        avis_test, created = Avis.objects.get_or_create(
            user=client_test,
            bien=bien_test,
            reservation=reservation_test,
            defaults={
                'note': 5,
                'commentaire': 'Excellent séjour ! Villa magnifique et propriétaire très accueillant.',
                'note_proprete': 5,
                'note_communication': 4,
                'note_emplacement': 5,
                'note_rapport_qualite_prix': 4,
                'recommande': True,
                'est_valide': True
            }
        )
        if created:
            self.stdout.write('✅ Avis de test créé')

        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 Données de test créées avec succès !\n'
                f'Client: {client_test.username} (mot de passe: testpass123)\n'
                f'Propriétaire: {proprietaire_test.username} (mot de passe: testpass123)\n'
                f'Bien: {bien_test.nom} (ID: {bien_test.id})\n'
                f'Réservations: {Reservation.objects.filter(bien=bien_test).count()}\n'
                f'Avis: {Avis.objects.filter(bien=bien_test).count()}'
            )
        )
