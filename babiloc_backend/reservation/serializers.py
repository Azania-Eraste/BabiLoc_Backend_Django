from rest_framework import serializers
from .models import Reservation, Bien, Media, Favori, Paiement, Tarif, Type_Bien, Document, Avis
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
from Auths.serializers import RegisterSerializer as AuthUserSerializer

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
            'id', 'user', 'bien', 'date_debut', 'date_fin',  # Change annonce_id to bien
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
    bien_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Media
        fields = ['id', 'image', 'bien_id']
        read_only_fields = ['id']
    
    def validate_bien_id(self, value):
        """Vérifier que le bien existe et appartient à l'utilisateur"""
        user = self.context['request'].user
        try:
            bien = Bien.objects.get(id=value, owner=user)
        except Bien.DoesNotExist:
            raise serializers.ValidationError("Ce bien n'existe pas ou ne vous appartient pas.")
        return value
    
    def create(self, validated_data):
        bien_id = validated_data.pop('bien_id')
        bien = Bien.objects.get(id=bien_id)
        return Media.objects.create(bien=bien, **validated_data)

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
    is_favori = serializers.SerializerMethodField()
    premiere_image = serializers.SerializerMethodField()
    type_bien = TypeBienSerializer(read_only=True)
    type_bien_id = serializers.IntegerField(write_only=True)
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Bien
        fields = [
            'id', 'nom', 'description', 'ville', 'noteGlobale', 'vues',
            'owner', 'disponibility', 'type_bien', 'type_bien_id', 'created_at', 'updated_at',
            'marque', 'modele', 'plaque', 'nb_places', 'nb_chambres', 
            'has_piscine', 'est_verifie', 'is_favori', 'premiere_image'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'vues', 'is_favori', 'premiere_image']

    def validate_type_bien_id(self, value):
        try:
            Type_Bien.objects.get(id=value)
        except Type_Bien.DoesNotExist:
            raise serializers.ValidationError("Ce type de bien n'existe pas.")
        return value

    def create(self, validated_data):
        type_bien_id = validated_data.pop('type_bien_id')
        type_bien = Type_Bien.objects.get(id=type_bien_id)
        validated_data['type_bien'] = type_bien
        return super().create(validated_data)

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
    
    class Meta:
        model = Reservation
        fields = ['bien', 'date_debut', 'date_fin', 'type_tarif', 'message']
    
    def validate(self, data):
        """Validation personnalisée"""
        bien = data.get('bien')
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        type_tarif = data.get('type_tarif')
        
        if date_debut >= date_fin:
            raise serializers.ValidationError("La date de fin doit être postérieure à la date de début.")
        
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
    bien = BienReservationSerializer()  # Change annonce_id to bien
    
    class Meta:
        model = Reservation
        fields = [
            'id', 'user_info', 'bien', 'date_debut', 'date_fin',  # Change annonce_id to bien
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
    # Change annonce_id to bien
    bien_nom = serializers.CharField(source='reservation.bien.nom', read_only=True)

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

class AvisSerializer(serializers.ModelSerializer):
    """Serializer pour les avis"""
    user = UserSerializer(read_only=True)
    bien_nom = serializers.CharField(source='bien.nom', read_only=True)
    note_moyenne_detaillee = serializers.ReadOnlyField()
    peut_repondre = serializers.SerializerMethodField()
    
    class Meta:
        model = Avis
        fields = [
            'id', 'user', 'bien', 'bien_nom', 'reservation', 'note',
            'commentaire', 'note_proprete', 'note_communication',
            'note_emplacement', 'note_rapport_qualite_prix', 'recommande',
            'note_moyenne_detaillee', 'reponse_proprietaire', 'date_reponse',
            'created_at', 'updated_at', 'peut_repondre'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 
            'note_moyenne_detaillee', 'peut_repondre'
        ]
    
    def get_peut_repondre(self, obj):
        """Vérifie si l'utilisateur connecté peut répondre à cet avis"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bien.owner == request.user and not obj.reponse_proprietaire
        return False

class AvisCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un avis"""
    
    class Meta:
        model = Avis
        fields = [
            'bien', 'reservation', 'note', 'commentaire',
            'note_proprete', 'note_communication', 'note_emplacement',
            'note_rapport_qualite_prix', 'recommande'
        ]
    
    def validate_reservation(self, value):
        """Valider que la réservation peut recevoir un avis"""
        user = self.context['request'].user
        
        # Vérifier que la réservation appartient à l'utilisateur
        if value.user != user:
            raise serializers.ValidationError("Cette réservation ne vous appartient pas.")
        
        # Vérifier que la réservation est terminée
        if value.status != 'completed':
            raise serializers.ValidationError("Vous ne pouvez donner un avis que pour une réservation terminée.")
        
        # Vérifier qu'un avis n'existe pas déjà
        if Avis.objects.filter(user=user, reservation=value).exists():
            raise serializers.ValidationError("Vous avez déjà donné un avis pour cette réservation.")
        
        return value
    
    def validate_bien(self, value):
        """Valider que le bien correspond à la réservation"""
        reservation = self.initial_data.get('reservation')
        if reservation:
            try:
                reservation_obj = Reservation.objects.get(id=reservation)
                if reservation_obj.bien != value:  # Change annonce_id to bien
                    raise serializers.ValidationError("Le bien ne correspond pas à la réservation.")
            except Reservation.DoesNotExist:
                raise serializers.ValidationError("Réservation introuvable.")
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ReponseProprietaireSerializer(serializers.ModelSerializer):
    """Serializer pour les réponses du propriétaire"""
    
    class Meta:
        model = Avis
        fields = ['reponse_proprietaire']
    
    def validate(self, data):
        if not data.get('reponse_proprietaire'):
            raise serializers.ValidationError("La réponse ne peut pas être vide.")
        return data
    
    def update(self, instance, validated_data):
        instance.reponse_proprietaire = validated_data['reponse_proprietaire']
        instance.date_reponse = timezone.now()
        instance.save()
        return instance

class StatistiquesAvisSerializer(serializers.Serializer):
    """Serializer pour les statistiques d'avis d'un bien"""
    note_moyenne = serializers.FloatField()
    nombre_avis = serializers.IntegerField()
    repartition_notes = serializers.DictField()
    pourcentage_recommandation = serializers.FloatField()
    notes_moyennes_categories = serializers.DictField()