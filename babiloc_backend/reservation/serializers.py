from rest_framework import serializers
from .models import Reservation, Bien, Media, Favori, Paiement, Tarif, Type_Bien, Document, CodePromo
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
from Auths.serializers import RegisterSerializer as AuthUserSerializer
from decimal import Decimal


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les informations utilisateur dans les réservations"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'number', 'date_joined']
        read_only_fields = ['id', 'username', 'date_joined']
        ref_name = 'ReservationUser'

class ReservationSerializer(serializers.ModelSerializer):
    """Serializer complet pour les réservations"""
    
    user = UserSerializer(read_only=True)
    duree_jours = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'annonce_id', 'date_debut', 'date_fin',
            'status', 'status_display', 'prix_total', 'message',
            'duree_jours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_frais_service(self, obj):
        return obj.frais_service

    def get_revenu_net_hote(self, obj):
        return obj.revenu_net_hote

# Serializer pour un Bien, incluant les tarifs liés


class TarifSerializer(serializers.ModelSerializer):
    bien_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Tarif
        fields = [
            'id',
            'type_tarif',
            'prix', 
            'bien_id'
            ]

    def validate_bien_id(self, value):
        user = self.context['request'].user
        try:
            bien = Bien.objects.get(id=value, owner=user)
        except Bien.DoesNotExist:
            raise serializers.ValidationError("Ce bien n'existe pas ou ne vous appartient pas.")
        return value

    def create(self, validated_data):
        bien_id = validated_data.pop('bien_id')
        bien = Bien.objects.get(id=bien_id)
        return Tarif.objects.create(bien=bien, **validated_data)

class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'image']

class TypeBienSerializer(serializers.ModelSerializer):
    class Meta:
        model = Type_Bien
        fields = '__all__'

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'nom', 'fichier', 'type']
        read_only_fields = ['date_upload']


class BienSerializer(serializers.ModelSerializer):
    tarifs = TarifSerializer(source='Tarifs_Biens_id', many=True, read_only=True)
    media = MediaSerializer(source='medias', many=True,read_only=True)
    premiere_image = serializers.SerializerMethodField()
    type_bien = TypeBienSerializer(read_only=True)
    is_favori = serializers.SerializerMethodField()
    owner = UserSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    class Meta:
        model = Bien
        fields = [
            'id',
            'nom',
            'description',
            'ville',
            'noteGlobale',
            'vues',
            'disponibility',
            'type_bien',
            'created_at',
            'is_favori',
            'owner',
            'updated_at',
            'nombre_likes',
            'premiere_image',
            'tarifs',
            'media',
            'documents',
        ]

    def validate_owner(self, value):
        if not value.is_vendor:
            raise serializers.ValidationError("L'utilisateur doit être un vendeur.")
        return value

    def get_is_favori(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Favori.objects.filter(user=user, bien=obj).exists()
        return False

    def get_premiere_image(self, obj):
        request = self.context.get('request')
        image_url = obj.get_first_image()
        return request.build_absolute_uri(image_url) if request and image_url else None



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

    def get_premiere_image(self, obj):
        request = self.context.get("request")
        image_url = obj.get_first_image()
        return request.build_absolute_uri(image_url) if request and image_url else None



class ReservationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une réservation"""
    code_promo = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Reservation
        fields = ['annonce_id', 'date_debut', 'date_fin', 'type_tarif', 'user', 'code_promo']

    def validate(self, data):
        annonce = data['annonce_id']
        date_debut = data['date_debut']
        date_fin = data['date_fin']

        if date_debut >= date_fin:
            raise serializers.ValidationError("La date de début doit être avant la date de fin.")

        conflits = Reservation.objects.filter(
            annonce_id=annonce,
            status__in=['pending', 'confirmed'],
            date_debut__lt=date_fin,
            date_fin__gt=date_debut
        )

        if conflits.exists():
            raise serializers.ValidationError("Ce bien est déjà réservé pendant cette période.")

        # Vérifie le code promo si fourni
        code_promo_str = self.initial_data.get('code_promo')
        if code_promo_str:
            try:
                code_promo = CodePromo.objects.get(nom=code_promo_str)
                data['code_promo_obj'] = code_promo  # transmis au create()
            except CodePromo.DoesNotExist:
                raise serializers.ValidationError("Code promotionnel invalide.")

        return data

    def create(self, validated_data):
        promo_obj = validated_data.pop('code_promo_obj', None)
        reservation = Reservation(**validated_data)

        tarif = reservation.get_tarif_bien()
        if not tarif:
            raise serializers.ValidationError("Aucun tarif défini pour ce bien.")

        nb_jours = (reservation.date_fin - reservation.date_debut).days or 1
        prix_total = Decimal(tarif.prix) * Decimal(nb_jours)

        # Applique la réduction si code promo
        if promo_obj:
            prix_total -= prix_total * promo_obj.reduction

        reservation.prix_total = prix_total
        reservation.save()

        # Ajoute la réservation à la promo
        if promo_obj:
            promo_obj.reservations.add(reservation)

        return reservation


class ReservationUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour le statut d'une réservation"""
    
    class Meta:
        model = Reservation
        fields = ['status', 'message']
    
    def validate_status(self, value):
        """Validation du changement de statut"""
        instance = self.instance
        if instance and instance.status == 'completed':
            raise serializers.ValidationError(
                "Une réservation terminée ne peut pas être modifiée."
            )
        return value

class ReservationListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes"""
    
    user_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    annonce_id = BienReservationSerializer()
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'user_info', 'annonce_id', 'date_debut', 'date_fin',
            'status', 'status_display', 'prix_total', 'created_at'
        ]
    
    def get_user_info(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': f"{obj.user.first_name} {obj.user.last_name}".strip(),
            'number': getattr(obj.user, 'number', '')
        }
    


class FavoriSerializer(serializers.ModelSerializer):
    """Serializer pour les favoris"""
    bien = BienSerializer(read_only=True)
    bien_id = serializers.IntegerField(write_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    

    class Meta:
        model = Favori
        fields = ['id', 'bien', 'bien_id', 'user_id','created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_bien_id(self, value):
        """Vérifier que le bien existe"""
        try:
            Bien.objects.get(id=value)
        except Bien.DoesNotExist:
            raise serializers.ValidationError("Ce bien n'existe pas.")
        return value
    
    def create(self, validated_data):
        bien_id = validated_data.pop('bien_id')
        bien = Bien.objects.get(id=bien_id)
        user = self.context['request'].user
        
        # Vérifier si le favori existe déjà
        if Favori.objects.filter(user=user, bien=bien).exists():
            raise serializers.ValidationError("Ce bien est déjà dans vos favoris.")
        
        return Favori.objects.create(user=user, bien=bien)

class FavoriListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour lister les favoris"""
    bien = BienSerializer(read_only=True)
    
    class Meta:
        model = Favori
        fields = ['id', 'bien', 'created_at']





class HistoriquePaiementSerializer(serializers.ModelSerializer):
    type_operation_display = serializers.CharField(source='get_type_operation_display', read_only=True)
    statut_paiement_display = serializers.CharField(source='get_statut_paiement_display', read_only=True)
    reservation_id = serializers.IntegerField(source='reservation.id', read_only=True)
    bien_nom = serializers.CharField(source='reservation.annonce_id.nom', read_only=True)

    class Meta:
        model = Paiement
        fields = [
            'id',
            'montant',
            'utilisateur',
            'mode',
            'statut_paiement',
            'statut_paiement_display',
            'type_operation',
            'type_operation_display',
            'reservation_id',
            'bien_nom',
            'created_at',
        ]