from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Bien, Tarif


@receiver(post_save, sender=Bien)
def auto_calculate_prices(sender, instance, created, **kwargs):
    """
    Signal qui recalcule automatiquement les prix hebdomadaire et mensuel
    après chaque sauvegarde d'un bien.
    """
    # Éviter les boucles infinies en vérifiant qu'on n'est pas déjà en train de sauvegarder
    if hasattr(instance, '_calculating_prices'):
        return
    
    print(f"🔔 SIGNAL - Auto-calcul des prix pour le bien: {instance.nom} (ID: {instance.id})")
    
    # Chercher le tarif journalier existant
    tarif_journalier = Tarif.objects.filter(
        bien=instance, 
        type_tarif='JOURNALIER'
    ).first()
    
    if tarif_journalier and tarif_journalier.prix > 0:
        prix_journalier = tarif_journalier.prix
        print(f"💰 SIGNAL - Prix journalier trouvé: {prix_journalier}")
        
        # Vérifier si les autres prix doivent être calculés
        tarif_hebdo = Tarif.objects.filter(bien=instance, type_tarif='HEBDOMADAIRE').first()
        tarif_mensuel = Tarif.objects.filter(bien=instance, type_tarif='MENSUEL').first()
        
        need_calculation = False
        
        if not tarif_hebdo or tarif_hebdo.prix == 0:
            need_calculation = True
            print(f"📈 SIGNAL - Prix hebdomadaire manquant ou à 0")
            
        if not tarif_mensuel or tarif_mensuel.prix == 0:
            need_calculation = True
            print(f"📈 SIGNAL - Prix mensuel manquant ou à 0")
        
        if need_calculation:
            print(f"⚡ SIGNAL - Calcul automatique des prix...")
            
            # Marquer l'instance pour éviter les boucles
            instance._calculating_prices = True
            
            # Calcul des prix avec réduction progressive
            prix_hebdomadaire = float(prix_journalier) * 7 * 0.85  # 15% de réduction pour 7 jours
            prix_mensuel = float(prix_journalier) * 30 * 0.70      # 30% de réduction pour 30 jours
            
            print(f"💰 SIGNAL - Prix hebdomadaire calculé: {prix_hebdomadaire}")
            print(f"💰 SIGNAL - Prix mensuel calculé: {prix_mensuel}")
            
            # Création/mise à jour du tarif hebdomadaire
            tarif_hebdo, created_hebdo = Tarif.objects.get_or_create(
                bien=instance,
                type_tarif='HEBDOMADAIRE',
                defaults={'prix': prix_hebdomadaire}
            )
            if not created_hebdo and tarif_hebdo.prix == 0:
                tarif_hebdo.prix = prix_hebdomadaire
                tarif_hebdo.save()
                print(f"💰 SIGNAL - Tarif hebdomadaire mis à jour: {prix_hebdomadaire}")
            elif created_hebdo:
                print(f"💰 SIGNAL - Tarif hebdomadaire créé: {prix_hebdomadaire}")
            
            # Création/mise à jour du tarif mensuel
            tarif_mensuel, created_mensuel = Tarif.objects.get_or_create(
                bien=instance,
                type_tarif='MENSUEL',
                defaults={'prix': prix_mensuel}
            )
            if not created_mensuel and tarif_mensuel.prix == 0:
                tarif_mensuel.prix = prix_mensuel
                tarif_mensuel.save()
                print(f"💰 SIGNAL - Tarif mensuel mis à jour: {prix_mensuel}")
            elif created_mensuel:
                print(f"💰 SIGNAL - Tarif mensuel créé: {prix_mensuel}")
            
            # Nettoyer le flag
            delattr(instance, '_calculating_prices')
            
            print(f"✅ SIGNAL - Calcul automatique terminé pour {instance.nom}")
        else:
            print(f"ℹ️  SIGNAL - Prix déjà corrects pour {instance.nom}")
    else:
        print(f"⚠️  SIGNAL - Aucun tarif journalier valide trouvé pour {instance.nom}")