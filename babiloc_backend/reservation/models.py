from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator,MaxValueValidator
from decimal import Decimal

User = get_user_model()

# ============================================================================
# MODÈLE TYPE_BIEN
# ============================================================================
# Représente les différents types de biens immobiliers disponibles à la location
# Exemples : Appartement, Maison, Studio, Villa, Chambre, Bureau, etc.
# Un type peut avoir plusieurs biens associés (relation One-to-Many)
class Type_Bien(models.Model):
    
    nom = models.CharField(max_length=250)  # Ex: "Appartement", "Villa"
    description = models.TextField()  # Description détaillée du type
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return self.nom


# ============================================================================
# MODÈLE BIEN
# ============================================================================
# Représente un bien immobilier mis en location sur la plateforme
# Exemple : "Appartement 2 pièces à Cocody" avec propriétaire, note, disponibilité
# Chaque bien appartient à un propriétaire et a un type spécifique
class Bien(models.Model):
    
    nom = models.CharField(max_length=250)  # Ex: "Villa moderne 4 chambres"
    description = models.TextField()  # Description complète du bien
    ville = models.CharField(max_length=100, verbose_name="Ville", default="Abidjan")
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix", default=0)
    
    noteGlobale = models.FloatField(  # Note moyenne sur 5 étoiles
        validators=[
            MinValueValidator(0.0),      # Note minimale : 0/5
            MaxValueValidator(5.0)       # Note maximale : 5/5
        ]
    ) 
    owner = models.ForeignKey(  # Propriétaire du bien
        User, 
        on_delete=models.CASCADE, 
        related_name='Propriétaire_bien',
        verbose_name="Propriétaire"
        )
    disponibility = models.BooleanField()  # True = disponible, False = occupé
    type_bien = models.ForeignKey(Type_Bien, related_name="biens", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def get_first_image(self):
        """Récupère la première image du bien pour l'affichage en liste"""
        return self.medias.first().image.url if self.medias.exists() else None

    def __str__(self):
        return self.nom


# ============================================================================
# MODÈLE TARIF
# ============================================================================
# Définit les prix de location pour chaque bien selon différentes périodes
# Exemples : "Prix par jour: 25000 FCFA", "Prix par semaine: 150000 FCFA"
# Un bien peut avoir plusieurs tarifs (journalier, hebdomadaire, mensuel)
class Tarif(models.Model):

    nom = models.CharField(max_length=250)  # Ex: "Tarif journalier", "Tarif mensuel"
    prix = models.FloatField(validators=[MinValueValidator(0.0)])  # Prix en FCFA
    bien = models.ForeignKey(Bien,on_delete=models.CASCADE, related_name='Tarifs_Biens_id')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé  le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    def __str__(self):
        return self.nom


# ============================================================================
# MODÈLE MEDIA
# ============================================================================
# Stocke les images/photos associées à chaque bien immobilier
# Exemple : Photos de la façade, salon, chambres, cuisine, etc.
# Un bien peut avoir plusieurs images pour le présenter aux locataires
class Media(models.Model):
    bien = models.ForeignKey('Bien', on_delete=models.CASCADE, related_name='medias')
    image = models.ImageField(upload_to='biens/')  # Images stockées dans media/biens/

    def __str__(self):
        return f"Image pour {self.bien.nom}"  # Correction: utiliser 'nom' au lieu de 'titre'


# ============================================================================
# MODÈLE RESERVATION
# ============================================================================
# Représente une demande de réservation d'un bien par un utilisateur
# Exemple : "Jean réserve la Villa à Cocody du 15/01 au 20/01 pour 125000 FCFA"
# Gère le cycle de vie : En attente → Confirmée → Terminée ou Annulée
class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
        ('completed', 'Terminée'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reservations',
        verbose_name="Utilisateur"
    )
    annonce = models.ForeignKey(
        Bien,
        on_delete=models.CASCADE, 
        related_name='reservations',
        verbose_name="Bien réservé"
    )
    
    date_debut = models.DateTimeField(verbose_name="Date de début")
    date_fin = models.DateTimeField(verbose_name="Date de fin")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Statut"
    )
    prix_total = models.DecimalField(  # Prix total calculé pour la période
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Prix total"
    )
    
    message = models.TextField(  # Message optionnel du client au propriétaire
        blank=True,
        null=True,
        verbose_name="Message du client"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        ordering = ['-created_at']  # Réservations les plus récentes en premier
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
    
    def __str__(self):
        return f"Reservation #{self.id} - {self.user.username}"
    
    @property
    def duree_jours(self):
        """Calcule la durée du séjour en jours"""
        return (self.date_fin - self.date_debut).days


# ============================================================================
# MODÈLE FAVORI
# ============================================================================
# Permet aux utilisateurs de sauvegarder leurs biens préférés
# Exemple : "Marie a ajouté l'Appartement Plateau aux favoris"
# Système de wishlist pour retrouver facilement les biens qui intéressent
class Favori(models.Model):
    user = models.ForeignKey(  # Utilisateur qui ajoute aux favoris
        User, 
        on_delete=models.CASCADE, 
        related_name='favoris',
        verbose_name="Utilisateur"
    )
    bien = models.ForeignKey(  # Bien ajouté aux favoris
        Bien, 
        on_delete=models.CASCADE, 
        related_name='favoris',
        verbose_name="Bien"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ajouté le")
    
    class Meta:
        # Un utilisateur ne peut pas ajouter le même bien deux fois
        unique_together = ('user', 'bien')  
        ordering = ['-created_at']  # Favoris les plus récents en premier
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
    
    def __str__(self):
        return f"{self.user.username} - {self.bien.nom}"