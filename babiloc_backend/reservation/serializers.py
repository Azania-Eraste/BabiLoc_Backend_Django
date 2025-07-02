from rest_framework import serializers
from .models import Reservation, Bien, Media, Favori, Paiement, Tarif, Type_Bien, Document, CodePromo, DisponibiliteHebdo, Avis
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
from Auths.serializers import RegisterSerializer as AuthUserSerializer
from decimal import Decimal
from datetime import timedelta


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

class DisponibiliteHebdoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisponibiliteHebdo  # Ce modèle doit exister
        fields = ['jours']


class BienSerializer(serializers.ModelSerializer):
    tarifs = TarifSerializer(source='Tarifs_Biens_id', many=True, read_only=True)
    media = MediaSerializer(source='medias', many=True, read_only=True)
    is_favori = serializers.SerializerMethodField()
    premiere_image = serializers.SerializerMethodField()
    type_bien = TypeBienSerializer(read_only=True)
    type_bien_id = serializers.IntegerField(write_only=True)
    owner = UserSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    disponibilite_hebdo = DisponibiliteHebdoSerializer(write_only=True, required=False)
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

    def create(self, validated_data):
        dispo_data = validated_data.pop('disponibilite_hebdo', None)
        bien = Bien.objects.create(**validated_data)

        if dispo_data:
            DisponibiliteHebdo.objects.create(bien=bien, **dispo_data)

        return bien




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
    annonce = serializers.PrimaryKeyRelatedField(queryset=Bien.objects.all())

    class Meta:
        model = Reservation
        fields = ['annonce', 'date_debut', 'date_fin', 'type_tarif', 'user', 'code_promo']

    def validate(self, data):
        annonce = data['annonce']
        date_debut = data['date_debut']
        date_fin = data['date_fin']

        # Sécurité : s’assurer que ce sont des dates valides
        if isinstance(date_debut, datetime):
            date_debut = date_debut.date()
        if isinstance(date_fin, datetime):
            date_fin = date_fin.date()

        if date_debut >= date_fin:
            raise serializers.ValidationError("La date de début doit être avant la date de fin.")

        # Conflits de réservations existantes
        conflits = Reservation.objects.filter(
            annonce_id=annonce.id,
            status__in=['pending', 'confirmed'],
            date_debut__lt=data['date_fin'],
            date_fin__gt=data['date_debut']
        )
        if conflits.exists():
            raise serializers.ValidationError("Ce bien est déjà réservé pendant cette période.")

        # Vérification des plages de disponibilités hebdo
        plages = annonce.plages_disponibilites.all()
        if not plages.exists():
            raise serializers.ValidationError("Ce bien n'a pas de plages de disponibilité définies.")

        current_date = data['date_debut'].date()
        end_date = data['date_fin'].date()
        while current_date <= end_date:
            jour_semaine = current_date.weekday()  # 0 = lundi, ..., 6 = dimanche
            dispo = plages.filter(
                jour=jour_semaine,
                date_debut__lte=current_date,
                date_fin__gte=current_date
            ).exists()
            if not dispo:
                raise serializers.ValidationError(
                    f"Le bien n'est pas disponible le {current_date.strftime('%A')} ({current_date})."
                )
            current_date += timedelta(days=1)

        # Vérifie le code promo si fourni
        code_promo_str = self.initial_data.get('code_promo')
        if code_promo_str:
            try:
                code_promo = CodePromo.objects.get(nom=code_promo_str)

                # ➕ Vérifie expiration du code promo s'il a ce champ
                if hasattr(code_promo, 'expiration') and code_promo.expiration and code_promo.expiration < datetime.now().date():
                    raise serializers.ValidationError("Ce code promotionnel est expiré.")

                data['code_promo_obj'] = code_promo
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

        # Applique la réduction si un code promo est utilisé
        if promo_obj:
            reduction = prix_total * promo_obj.reduction
            prix_total -= reduction

        reservation.prix_total = prix_total
        reservation.save()

        # Ajout dans la promo si applicable
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
                if reservation_obj.annonce_id != value:
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