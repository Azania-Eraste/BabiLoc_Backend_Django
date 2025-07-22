from rest_framework import serializers
from .models import (
    Reservation, Bien, Media, Favori, TagBien, Tarif, Type_Bien, 
    Document, Avis, DisponibiliteHebdo, Ville, CodePromo,
    HistoriqueStatutReservation, RevenuProprietaire
)
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from datetime import timedelta

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les informations utilisateur dans les réservations"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'username']

class ReservationSerializer(serializers.ModelSerializer):
    """Serializer complet pour les réservations"""
    user = UserSerializer(read_only=True)
    bien_nom = serializers.CharField(source='bien.nom', read_only=True)
    duree_jours = serializers.ReadOnlyField()
    commission_plateforme = serializers.ReadOnlyField()
    revenu_proprietaire = serializers.ReadOnlyField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'bien', 'bien_nom', 'type_tarif',
            'date_debut', 'date_fin', 'status', 'prix_total',
            'message', 'created_at', 'updated_at', 'duree_jours',
            'commission_plateforme', 'revenu_proprietaire', 'confirmed_at'
        ]

class TarifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarif
        fields = ['id', 'prix', 'type_tarif', 'bien', 'created_at', 'updated_at']

class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'bien', 'image', 'created_at']

class TagBienSerializer(serializers.ModelSerializer):
    """Serializer pour les tags de bien"""
    class Meta:
        model = TagBien
        fields = ['id', 'nom', 'description', 'iconName', 'created_at']

class TypeBienSerializer(serializers.ModelSerializer):
    """Serializer pour les types de bien"""
    tags = TagBienSerializer(many=True, read_only=True)
    
    class Meta:
        model = Type_Bien
        fields = ['id', 'nom', 'description', 'tags', 'created_at', 'updated_at']

class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'bien', 'nom', 'type', 'fichier', 'image',
            'file_url', 'file_type', 'file_extension', 'created_at'
        ]

    def get_file_url(self, obj):
        return obj.get_file_url()

    def get_file_type(self, obj):
        return obj.get_file_type()

    def get_file_extension(self, obj):
        return obj.get_file_extension()

class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = ['id', 'nom', 'pays', 'created_at']

class BienSerializer(serializers.ModelSerializer):
    tarifs = TarifSerializer(many=True, read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    ville_nom = serializers.CharField(source='ville.nom', read_only=True)
    type_bien_nom = serializers.CharField(source='type_bien.nom', read_only=True)
    nombre_likes = serializers.ReadOnlyField()
    first_image = serializers.SerializerMethodField()

    class Meta:
        model = Bien
        fields = [
            'id', 'nom', 'description', 'ville', 'ville_nom', 'noteGlobale',
            'vues', 'owner', 'owner_username', 'disponibility', 'type_bien',
            'type_bien_nom', 'created_at', 'updated_at', 'tarifs', 'media',
            'nombre_likes', 'first_image', 'est_verifie', 'chauffeur',
            'prix_chauffeur', 'marque', 'modele', 'plaque', 'nb_places',
            'carburant', 'transmission', 'nb_chambres', 'has_piscine'
        ]

    def get_first_image(self, obj):
        return obj.get_first_image()

class ReservationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            'bien', 'type_tarif', 'date_debut', 'date_fin', 'message'
        ]

    def validate(self, data):
        # Validation des dates
        if data['date_debut'] >= data['date_fin']:
            raise serializers.ValidationError("La date de fin doit être après la date de début")
        
        # Validation que la date de début n'est pas dans le passé
        if data['date_debut'] < timezone.now():
            raise serializers.ValidationError("La date de début ne peut pas être dans le passé")
        
        return data

class ReservationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['status', 'message']

class ReservationListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    bien_nom = serializers.CharField(source='bien.nom', read_only=True)
    ville = serializers.CharField(source='bien.ville.nom', read_only=True)
    first_image = serializers.CharField(source='bien.get_first_image', read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'bien', 'bien_nom', 'ville', 'first_image',
            'date_debut', 'date_fin', 'status', 'prix_total',
            'created_at', 'owner_name', 'type_tarif'
        ]

    def get_owner_name(self, obj):
        return f"{obj.bien.owner.first_name} {obj.bien.owner.last_name}".strip() or obj.bien.owner.username

class FavoriSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    bien = BienSerializer(read_only=True)

    class Meta:
        model = Favori
        fields = ['id', 'user', 'bien', 'created_at']

class FavoriListSerializer(serializers.ModelSerializer):
    bien_nom = serializers.CharField(source='bien.nom', read_only=True)
    bien_ville = serializers.CharField(source='bien.ville.nom', read_only=True)
    first_image = serializers.CharField(source='bien.get_first_image', read_only=True)
    
    class Meta:
        model = Favori
        fields = ['id', 'bien', 'bien_nom', 'bien_ville', 'first_image', 'created_at']

class AvisSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    bien_nom = serializers.CharField(source='bien.nom', read_only=True)
    note_moyenne_detaillee = serializers.ReadOnlyField()

    class Meta:
        model = Avis
        fields = [
            'id', 'user', 'user_name', 'bien', 'bien_nom', 'reservation',
            'note', 'commentaire', 'note_proprete', 'note_communication',
            'note_emplacement', 'note_rapport_qualite_prix', 'recommande',
            'est_valide', 'reponse_proprietaire', 'date_reponse',
            'created_at', 'note_moyenne_detaillee'
        ]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

class AvisCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avis
        fields = [
            'bien', 'reservation', 'note', 'commentaire',
            'note_proprete', 'note_communication', 'note_emplacement',
            'note_rapport_qualite_prix', 'recommande'
        ]

class ReponseProprietaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avis
        fields = ['reponse_proprietaire']

class StatistiquesAvisSerializer(serializers.Serializer):
    note_moyenne = serializers.FloatField()
    total_avis = serializers.IntegerField()
    repartition_notes = serializers.DictField()
    pourcentage_recommandation = serializers.FloatField()
    notes_detaillees = serializers.DictField()