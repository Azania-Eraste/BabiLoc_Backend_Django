from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

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
    annonce_id = models.PositiveIntegerField(verbose_name="ID de l'annonce")
    
    date_debut = models.DateTimeField(verbose_name="Date de début")
    date_fin = models.DateTimeField(verbose_name="Date de fin")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Statut"
    )
    prix_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Prix total"
    )
    
    message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message du client"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
    
    def __str__(self):
        return f"Reservation #{self.id} - {self.user.username}"
    
    @property
    def duree_jours(self):
        """Calcule la durée en jours"""
        return (self.date_fin - self.date_debut).days