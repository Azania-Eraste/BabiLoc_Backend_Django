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
        fields = ['id', 'nom', 'pays']
        read_only_fields = ['id']
    
    def validate_nom(self, value):
        """Validation pour s'assurer que le nom de la ville n'est pas vide"""
        if not value:
            raise serializers.ValidationError("Le nom de la ville ne peut pas être vide.")
        return value

class DisponibiliteHebdoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisponibiliteHebdo
        fields = ['jours']  # ou ce que tu utilises

class TypeCarburantSerializer(serializers.Serializer):
    """Serializer pour les choix de type de carburant"""
    value = serializers.CharField()
    label = serializers.CharField()

class TypeTransmissionSerializer(serializers.Serializer):
    """Serializer pour les choix de type de transmission"""
    value = serializers.CharField()
    label = serializers.CharField()


class BienSerializer(serializers.ModelSerializer):
    disponibilite_hebdo = DisponibiliteHebdoSerializer(required=False)
    tarifs = TarifSerializer( many=True, read_only=True)  # OK selon ton modèle
    media = MediaSerializer(source='medias', many=True, read_only=True)           # à adapter si nécessaire
    is_favori = serializers.SerializerMethodField()
    nombre_likes = serializers.SerializerMethodField()
    premiere_image = serializers.SerializerMethodField()
    type_bien = TypeBienSerializer(read_only=True)
    owner = UserSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    ville = VilleSerializer(read_only=True)
    ville_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    type_bien_id = serializers.IntegerField(write_only=True, required=True)
    tags = TagBienSerializer(many=True, read_only=True)  # Tags associés au bien
    tag_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    carburant_display = serializers.CharField(source='get_carburant_display', read_only=True)
    transmission_display = serializers.CharField(source='get_transmission_display', read_only=True)

    class Meta:
        model = Bien
        fields = [
            'id', 'nom', 'description', 'ville', 'ville_id',
            'noteGlobale', 'disponibility', 'vues', 'type_bien', 'type_bien_id', 
            'owner', 'is_favori', 'premiere_image', 'documents', 'tarifs', 'media','tags', 'tag_ids',
            'marque', 'modele', 'plaque', 'nb_places', 'carburant', 'carburant_display', 'transmission', 'transmission_display', 'nb_chambres', "chauffeur", 'prix_chauffeur',
            'has_piscine', 'est_verifie', 'created_at', 'updated_at', 'nombre_likes', 'disponibilite_hebdo',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'vues']

    def validate_type_bien_id(self, value):
        if not Type_Bien.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ce type de bien n'existe pas.")
        return value
    
    def validate_ville_id(self, value):
        if value and not Ville.objects.filter(id=value).exists():
            raise serializers.ValidationError("Cette ville n'existe pas.")
        return value
    
    def validate_tag_ids(self, value):
        if value:
            existing_tags = TagBien.objects.filter(id__in=value).count()
            if existing_tags != len(value):
                raise serializers.ValidationError("Un ou plusieurs tags n'existent pas.")
        return value

    def get_nombre_likes(self, obj):
        return Favori.objects.filter(bien=obj).count()

    def get_is_favori(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favori.objects.filter(user=request.user, bien=obj).exists()
        return False

    def get_premiere_image(self, obj):
        request = self.context.get('request')
        image_url = obj.get_first_image()
        if request and image_url:
            return request.build_absolute_uri(image_url)
        return image_url

    def create(self, validated_data):
        tarifs_data = validated_data.pop('tarifs', [])
        dispo_data = validated_data.pop('disponibilite_hebdo', None)
        media_data = validated_data.pop('media', [])
        document_data = validated_data.pop('documents', [])
        tag_ids = validated_data.pop('tag_ids', [])

        # Gestion du type de bien
        type_bien_id = validated_data.pop('type_bien_id')
        type_bien = Type_Bien.objects.get(id=type_bien_id)
        validated_data['type_bien'] = type_bien

        # Gestion de la ville
        ville_id = validated_data.pop('ville_id', None)
        if ville_id:
            ville = Ville.objects.get(id=ville_id)
            validated_data['ville'] = ville

        bien = Bien.objects.create(**validated_data)

        # Ajout des tags
        if tag_ids:
            tags = TagBien.objects.filter(id__in=tag_ids)
            bien.tags.set(tags)

        # Création des objets liés
        for tarif in tarifs_data:
            Tarif.objects.create(bien=bien, **tarif)

        for media in media_data:
            Media.objects.create(bien=bien, **media)

        for doc in document_data:
            Document.objects.create(bien=bien, **doc)

        if dispo_data:
            DisponibiliteHebdo.objects.create(bien=bien, **dispo_data)

        return bien

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)
        ville_id = validated_data.pop('ville_id', None)
        type_bien_id = validated_data.pop('type_bien_id', None)

        # Mise à jour des champs de base
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Gestion du type de bien
        if type_bien_id:
            type_bien = Type_Bien.objects.get(id=type_bien_id)
            instance.type_bien = type_bien

        # Gestion de la ville
        if ville_id:
            ville = Ville.objects.get(id=ville_id)
            instance.ville = ville

        instance.save()

        # Mise à jour des tags
        if tag_ids is not None:
            tags = TagBien.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)

        return instance






class BienReservationSerializer(serializers.ModelSerializer):
    premiere_image = serializers.SerializerMethodField()
    type_bien = TypeBienSerializer(read_only=True)

    class Meta:
        model = Bien
        fields = [
            "id",
            "nom",
            "description",
            "type_bien",
            "premiere_image",
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
        
        # Vérifier qu'un tarif existe pour ce bien et ce type
        tarif_exists = bien.Tarifs_Biens_id.filter(type_tarif=type_tarif).exists()
        if not tarif_exists:
            available_tarifs = list(bien.Tarifs_Biens_id.values_list('type_tarif', flat=True))
            raise serializers.ValidationError(
                f"Aucun tarif '{type_tarif}' disponible pour ce bien. "
                f"Tarifs disponibles: {available_tarifs}"
            )
        
        # Vérifier les conflits de dates
        conflits = Reservation.objects.filter(
            bien=bien,
            date_debut__lt=date_fin,
            date_fin__gt=date_debut,
            status__in=['pending', 'confirmed']
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        if conflits.exists():
            raise serializers.ValidationError("Ce bien est déjà réservé pour cette période.")
        
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