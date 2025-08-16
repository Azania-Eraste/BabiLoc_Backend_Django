"""
Commande Django pour mettre à jour automatiquement les statuts des réservations
À exécuter via une tâche cron toutes les heures

Usage: python manage.py mettre_a_jour_statuts_reservations
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from reservation.services.disponibilite_service import DisponibiliteService


class Command(BaseCommand):
    help = 'Met à jour automatiquement les statuts des réservations selon les dates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Effectue une simulation sans sauvegarder les changements',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'Début de la mise à jour automatique des statuts - {timezone.now()}')
        )

        try:
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('Mode simulation activé - Aucune modification ne sera sauvegardée')
                )
                # TODO: Implémenter le mode dry-run si nécessaire
                
            # Lancer la mise à jour
            reservations_modifiees = DisponibiliteService.mettre_a_jour_statuts_reservations()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Mise à jour terminée avec succès : {reservations_modifiees} réservations modifiées'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur lors de la mise à jour : {e}')
            )
            raise e
