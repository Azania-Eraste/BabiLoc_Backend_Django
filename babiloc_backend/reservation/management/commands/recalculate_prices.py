from django.core.management.base import BaseCommand
from reservation.models import Bien, Tarif
from reservation.serializers import BienSerializer


class Command(BaseCommand):
    help = 'Recalcule automatiquement les prix hebdomadaires et mensuels pour tous les biens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le recalcul même si les prix existent déjà',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Début du recalcul automatique des prix...'))
        
        # Récupérer tous les biens qui ont un tarif journalier
        biens_avec_tarif_journalier = Bien.objects.filter(
            Tarifs_Biens_id__type_tarif='JOURNALIER'
        ).distinct()
        
        self.stdout.write(f'📊 {biens_avec_tarif_journalier.count()} biens trouvés avec un tarif journalier')
        
        serializer = BienSerializer()
        biens_traites = 0
        biens_mis_a_jour = 0
        
        for bien in biens_avec_tarif_journalier:
            self.stdout.write(f'\n🔍 Traitement du bien: {bien.nom} (ID: {bien.id})')
            
            # Récupérer le tarif journalier
            tarif_journalier = Tarif.objects.filter(
                bien=bien, 
                type_tarif='JOURNALIER'
            ).first()
            
            if not tarif_journalier:
                self.stdout.write(f'⚠️  Aucun tarif journalier trouvé pour {bien.nom}')
                continue
                
            prix_journalier = tarif_journalier.prix
            self.stdout.write(f'💰 Prix journalier: {prix_journalier} FCFA')
            
            # Vérifier si les prix hebdomadaire et mensuel existent et ne sont pas à 0
            tarif_hebdo = Tarif.objects.filter(bien=bien, type_tarif='HEBDOMADAIRE').first()
            tarif_mensuel = Tarif.objects.filter(bien=bien, type_tarif='MENSUEL').first()
            
            needs_update = False
            
            if options['force']:
                needs_update = True
                self.stdout.write('🔄 Recalcul forcé activé')
            else:
                if not tarif_hebdo or tarif_hebdo.prix == 0:
                    needs_update = True
                    self.stdout.write('📈 Prix hebdomadaire manquant ou à 0')
                    
                if not tarif_mensuel or tarif_mensuel.prix == 0:
                    needs_update = True
                    self.stdout.write('📈 Prix mensuel manquant ou à 0')
            
            if needs_update:
                self.stdout.write('⚡ Lancement du recalcul automatique...')
                serializer._create_automatic_tarifs(bien, prix_journalier)
                biens_mis_a_jour += 1
                self.stdout.write(self.style.SUCCESS('✅ Prix recalculés avec succès!'))
            else:
                self.stdout.write('ℹ️  Prix déjà corrects, pas de mise à jour nécessaire')
            
            biens_traites += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Recalcul terminé!\n'
                f'📊 Biens traités: {biens_traites}\n'
                f'🔄 Biens mis à jour: {biens_mis_a_jour}'
            )
        )