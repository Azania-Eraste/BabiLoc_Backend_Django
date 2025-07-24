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
            'id', 'nom', 'description', 'ville', 
            'noteGlobale', 'disponibility', 'vues', 'type_bien', 'type_bien_id', 
            'owner', 'is_favori', 'premiere_image', 'documents', 'tarifs', 'media',
            'marque', 'modele', 'plaque', 'nb_places', 'nb_chambres', "chauffeur", 'prix_chauffeur',
            'has_piscine', 'est_verifie', 'created_at', 'updated_at', 'nombre_likes', 'disponibilite_hebdo',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'vues']

    def validate_type_bien_id(self, value):
        if not Type_Bien.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ce type de bien n'existe pas.")
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

        type_bien_id = validated_data.pop('type_bien_id')
        type_bien = Type_Bien.objects.get(id=type_bien_id)
        validated_data['type_bien'] = type_bien

        bien = Bien.objects.create(**validated_data)

        for tarif in tarifs_data:
            Tarif.objects.create(bien=bien, **tarif)

        for media in media_data:
            Media.objects.create(bien=bien, **media)

        for doc in document_data:
            Document.objects.create(bien=bien, **doc)

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
        tarif_exists = bien.tarifs.filter(type_tarif=type_tarif).exists()
        if not tarif_exists:
            available_tarifs = list(bien.tarifs.values_list('type_tarif', flat=True))
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
    notes_moyennes_categories = serializers.DictField()

class FactureSerializer(serializers.ModelSerializer):
    """Serializer pour les factures"""
    
    numero_facture = serializers.CharField(read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_facture_display = serializers.CharField(source='get_type_facture_display', read_only=True)
    fichier_pdf_url = serializers.SerializerMethodField()
    
    reservation_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Facture
        fields = [
            'id', 'numero_facture', 'type_facture', 'type_facture_display',
            'client_nom', 'client_email', 'client_telephone',
            'hote_nom', 'hote_email', 'hote_telephone',
            'montant_ht', 'tva_taux', 'montant_tva', 'montant_ttc',
            'commission_plateforme', 'montant_net_hote',
            'statut', 'statut_display', 'date_emission', 'date_echeance',
            'date_paiement', 'fichier_pdf_url', 'reservation_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'numero_facture', 'montant_ht', 'montant_tva', 'montant_ttc',
            'commission_plateforme', 'montant_net_hote', 'date_emission',
            'created_at', 'updated_at'
        ]
    
    def get_fichier_pdf_url(self, obj):
        """Retourne l'URL du fichier PDF"""
        request = self.context.get('request')
        if obj.fichier_pdf and request:
            return request.build_absolute_uri(obj.fichier_pdf.url)
        return None
    
    def get_reservation_details(self, obj):
        """Retourne les détails de la réservation"""
        if obj.reservation:
            return {
                'id': obj.reservation.id,
                'bien_nom': obj.reservation.bien.nom,
                'date_debut': obj.reservation.date_debut,
                'date_fin': obj.reservation.date_fin,
                'duree_jours': obj.reservation.duree_jours,
                'prix_total': obj.reservation.prix_total
            }
        return None

class FactureCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une facture"""
    
    class Meta:
        model = Facture
        fields = [
            'reservation', 'paiement', 'client_nom', 'client_email',
            'client_telephone', 'client_adresse', 'hote_nom', 'hote_email',
            'hote_telephone', 'date_echeance', 'type_facture'
        ]
    
    def validate_reservation(self, value):
        """Valider que la réservation est payée"""
        # Use the constant from the Paiement model
        if not value.paiements.filter(statut_paiement=Paiement.STATUT_EFFECTUE).exists():
            raise serializers.ValidationError("La réservation doit être payée pour générer une facture.")
        return value
    
    def validate_paiement(self, value):
        """Valider que le paiement est effectué"""
        if value and value.statut_paiement != Paiement.STATUT_EFFECTUE:
            raise serializers.ValidationError("Le paiement doit être effectué pour générer une facture.")
        return value
    
    def validate(self, data):
        """Validation globale"""
        reservation = data.get('reservation')
        paiement = data.get('paiement')
        
        # Si un paiement est fourni, vérifier qu'il correspond à la réservation
        if paiement and reservation and paiement.reservation != reservation:
            raise serializers.ValidationError("Le paiement ne correspond pas à la réservation.")
        
        return data
    
    def create(self, validated_data):
        """Créer la facture avec les données calculées automatiquement"""
        reservation = validated_data['reservation']
        
        # Compléter les données automatiquement si pas fournies
        if not validated_data.get('client_nom'):
            user = reservation.user
            validated_data['client_nom'] = f"{user.first_name} {user.last_name}".strip() or user.username
        
        if not validated_data.get('client_email'):
            validated_data['client_email'] = reservation.user.email
        
        if not validated_data.get('hote_nom'):
            owner = reservation.bien.owner
            validated_data['hote_nom'] = f"{owner.first_name} {owner.last_name}".strip() or owner.username
        
        if not validated_data.get('hote_email'):
            validated_data['hote_email'] = reservation.bien.owner.email
        
        # Créer la facture
        facture = super().create(validated_data)
        return facture