import re
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils import timezone  # ✅ Add this import
from .models import CustomUser, DocumentUtilisateur, HistoriqueParrainage, CodePromoParrainage
from reservation.models import Bien  # ✅ Changé de BienSerializer vers le modèle
from django.db.models import Sum, Count
from decimal import Decimal


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Garder le champ username par défaut pour la connexion
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            try:
                # Trouver l'utilisateur par username
                user = CustomUser.objects.get(username=username)

                # Vérifier si le compte est actif
                if not user.is_active:
                    raise serializers.ValidationError({
                        'detail': 'Compte non activé. Veuillez vérifier votre email et saisir le code OTP.',
                        'user_id': user.id,
                        'requires_activation': True
                    })
                
                # ✅ Authentifier l'utilisateur directement
                from django.contrib.auth import authenticate
                authenticated_user = authenticate(username=user.username, password=password)
                
                if authenticated_user is None:
                    raise serializers.ValidationError('Mot de passe incorrect.')
                
                # ✅ Préparer les données pour la génération du token
                # Ne pas appeler super().validate() car nous gérons nous-mêmes l'authentification
                refresh = self.get_token(authenticated_user)
                
                return {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'email': authenticated_user.email,
                    'username': authenticated_user.username,
                    'is_vendor': authenticated_user.is_vendor,
                    'code_parrainage': authenticated_user.code_parrainage,
                }
                
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError('Aucun compte avec ce nom d\'utilisateur.')
        
        raise serializers.ValidationError('Nom d\'utilisateur et mot de passe requis.')
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Ajouter des données personnalisées au token
        token['email'] = user.email
        token['username'] = user.username
        token['is_vendor'] = user.is_vendor
        token['code_parrainage'] = user.code_parrainage
        return token


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour l'utilisateur avec les biens associés"""
    
    def to_representation(self, instance):
        # Import dynamique pour éviter les imports circulaires
        from reservation.serializers import BienSerializer
        
        representation = super().to_representation(instance)
        
        # Serializer les biens du propriétaire
        biens = instance.Propriétaire_bien.all()
        representation['Propriétaire_bien'] = BienSerializer(
            biens, 
            many=True, 
            context=self.context
        ).data
        
        return representation
    
    class Meta:
        model = CustomUser
        fields = (
            'id','username', 'email', 'first_name', 'last_name',
            'number', 'birthdate', 'password','reservations',
            'carte_identite','permis_conduire','est_verifie',
            'is_vendor','date_joined','photo_profil','image_banniere',
            'Propriétaire_bien', 'code_parrainage', 'nb_parrainages',
            'recompense_parrainage'
        )
        ref_name = 'AuthUser'


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    code_parrainage_utilise = serializers.CharField(max_length=20, required=False, write_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'number', 'birthdate', 'password', 'password2', 'is_vendor',
            'est_verifie', 'code_parrainage_utilise'
        )

    def validate_number(self, value):
        import re
        pattern = r'^\+\d{1,4}\d{6,12}$'
        if not re.match(pattern, value.replace(" ", "")):
            raise serializers.ValidationError("Numéro invalide. Format attendu : +225XXXXXXXXX")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        code_parrainage_utilise = validated_data.pop('code_parrainage_utilise', None)
        
        # ✅ Fix: Créer l'utilisateur sans appeler save() immédiatement
        password = validated_data.pop('password')
        
        # ✅ Créer l'instance sans la sauvegarder
        user = CustomUser(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            number=validated_data['number'],
            birthdate=validated_data['birthdate'],
            is_vendor=validated_data.get('is_vendor', False),
            carte_identite=validated_data.get('carte_identite', None),
            permis_conduire=validated_data.get('permis_conduire', None),
            est_verifie=validated_data.get('est_verifie', False),
            is_active=False
        )
        
        # ✅ Définir le mot de passe
        user.set_password(password)
        
        # ✅ Traiter le code de parrainage AVANT la sauvegarde
        if code_parrainage_utilise:
            try:
                parrain = CustomUser.objects.get(code_parrainage=code_parrainage_utilise)
                user.parrain = parrain
                user.date_parrainage = timezone.now()
            except CustomUser.DoesNotExist:
                pass
        
        # ✅ Maintenant sauvegarder
        user.save()
        return user

class OTPVerificationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    otp_code = serializers.CharField(max_length=4, min_length=4)

class DocumentUtilisateurSerializer(serializers.ModelSerializer):
    """Serializer pour les documents utilisateur"""
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    type_document_display = serializers.CharField(source='get_type_document_display', read_only=True)
    statut_verification_display = serializers.CharField(source='get_statut_verification_display', read_only=True)
    
    class Meta:
        model = DocumentUtilisateur
        fields = [
            'id', 'nom', 'type_document', 'type_document_display',
            'fichier', 'image', 'file_url', 'file_type', 'file_extension',
            'statut_verification', 'statut_verification_display',
            'date_expiration', 'is_expired', 'commentaire_moderateur',
            'date_upload', 'date_verification'
        ]
        read_only_fields = [
            'id', 'date_upload', 'date_verification', 'statut_verification',
            'commentaire_moderateur', 'is_expired'
        ]
    
    def get_file_url(self, obj):
        """Retourne l'URL complète du fichier ou de l'image"""
        request = self.context.get('request')
        file_url = obj.get_file_url()
        if request and file_url:
            return request.build_absolute_uri(file_url)
        return file_url
    
    def get_file_type(self, obj):
        """Retourne le type de fichier"""
        return obj.get_file_type()
    
    def get_file_extension(self, obj):
        """Retourne l'extension du fichier"""
        return obj.get_file_extension()
    
    def get_is_expired(self, obj):
        """Vérifie si le document est expiré"""
        return obj.is_expired()
    
    def validate(self, attrs):
        """Validation personnalisée"""
        fichier = attrs.get('fichier')
        image = attrs.get('image')
        
        if not fichier and not image:
            raise serializers.ValidationError('Vous devez fournir soit un fichier soit une image.')
        
        if fichier and image:
            raise serializers.ValidationError('Vous ne pouvez pas fournir à la fois un fichier et une image.')
        
        return attrs

class DocumentModerationSerializer(serializers.ModelSerializer):
    """Serializer pour la modération des documents"""
    
    class Meta:
        model = DocumentUtilisateur
        fields = [
            'id', 'statut_verification', 'commentaire_moderateur'
        ]
    
    def validate_statut_verification(self, value):
        """Validation du statut"""
        if value not in ['approuve', 'refuse']:
            raise serializers.ValidationError("Le statut doit être 'approuve' ou 'refuse'.")
        return value
    
    def update(self, instance, validated_data):
        """Mise à jour avec enregistrement de la date et du modérateur"""
        from django.utils import timezone
        
        instance.statut_verification = validated_data.get('statut_verification', instance.statut_verification)
        instance.commentaire_moderateur = validated_data.get('commentaire_moderateur', instance.commentaire_moderateur)
        instance.date_verification = timezone.now()
        instance.moderateur = self.context['request'].user
        instance.save()
        
        return instance

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour le profil utilisateur avec documents"""
    documents_verification = DocumentUtilisateurSerializer(many=True, read_only=True)
    documents_approuves = serializers.SerializerMethodField()
    est_completement_verifie = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'number', 'birthdate', 'is_vendor', 'est_verifie',
            'documents_verification', 'documents_approuves', 'est_completement_verifie'
        ]
        ref_name = 'UserProfile'
        read_only_fields = ['id', 'username', 'est_verifie']
    
    def get_documents_approuves(self, obj):
        """Retourne les types de documents approuvés"""
        return list(obj.documents_verification.filter(
            statut_verification='approuve'
        ).values_list('type_document', flat=True))
    
    def get_est_completement_verifie(self, obj):
        """Vérifie si l'utilisateur a au moins CNI + permis approuvés"""
        documents_approuves = self.get_documents_approuves(obj)
        return 'carte_identite' in documents_approuves and 'permis_conduire' in documents_approuves

class ParrainageSerializer(serializers.ModelSerializer):
    """Serializer pour les informations de parrainage"""
    
    parrain_info = serializers.SerializerMethodField()
    nombre_filleuls = serializers.SerializerMethodField()
    revenus_parrainage = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'code_parrainage', 'parrain_info', 'date_parrainage',
            'parrainage_actif', 'points_parrainage', 'nombre_filleuls',
            'revenus_parrainage'
        ]
    
    def get_parrain_info(self, obj):
        """Retourne les infos du parrain"""
        if obj.parrain:
            return {
                'id': obj.parrain.id,
                'username': obj.parrain.username,
                'first_name': obj.parrain.first_name,
                'last_name': obj.parrain.last_name,
                'code_parrainage': obj.parrain.code_parrainage
            }
        return None
    
    def get_nombre_filleuls(self, obj):
        """Retourne le nombre de filleuls"""
        return obj.get_nombre_filleuls()
    
    def get_revenus_parrainage(self, obj):
        """Retourne les revenus du parrainage"""
        return obj.get_revenus_parrainage()


class FilleulSerializer(serializers.ModelSerializer):
    """Serializer pour les filleuls"""
    
    revenus_generes = serializers.SerializerMethodField()
    premiere_reservation = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'date_parrainage', 'parrainage_actif', 'revenus_generes',
            'premiere_reservation'
        ]
    
    def get_revenus_generes(self, obj):
        """Calcule les revenus générés par ce filleul"""
        from django.db.models import Sum
        return obj.historique_filleul.aggregate(
            total=Sum('montant_recompense')
        )['total'] or 0
    
    def get_premiere_reservation(self, obj):
        """Vérifie si le filleul a fait sa première réservation"""
        return obj.reservations.exists()


class HistoriqueParrainageSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique de parrainage"""
    
    parrain_info = serializers.SerializerMethodField()
    filleul_info = serializers.SerializerMethodField()
    type_action_display = serializers.CharField(source='get_type_action_display', read_only=True)
    statut_recompense_display = serializers.CharField(source='get_statut_recompense_display', read_only=True)
    
    class Meta:
        model = HistoriqueParrainage
        fields = [
            'id', 'parrain_info', 'filleul_info', 'type_action', 'type_action_display',
            'montant_recompense', 'points_recompense', 'description',
            'statut_recompense', 'statut_recompense_display',
            'date_action', 'date_recompense'
        ]
    
    def get_parrain_info(self, obj):
        return {
            'id': obj.parrain.id,
            'username': obj.parrain.username,
            'first_name': obj.parrain.first_name,
            'last_name': obj.parrain.last_name
        }
    
    def get_filleul_info(self, obj):
        return {
            'id': obj.filleul.id,
            'username': obj.filleul.username,
            'first_name': obj.filleul.first_name,
            'last_name': obj.filleul.last_name
        }


class CodePromotionParrainageSerializer(serializers.ModelSerializer):
    """Serializer pour les codes promo de parrainage"""
    
    parrain_info = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    utilisations_restantes = serializers.SerializerMethodField()
    
    class Meta:
        model = CodePromoParrainage
        fields = [
            'id', 'code', 'parrain_info', 'pourcentage_reduction',
            'montant_reduction', 'nombre_utilisations_max',
            'nombre_utilisations', 'utilisations_restantes',
            'date_expiration', 'est_actif', 'is_valid', 'date_creation'
        ]
    
    def get_parrain_info(self, obj):
        return {
            'id': obj.parrain.id,
            'username': obj.parrain.username,
            'code_parrainage': obj.parrain.code_parrainage
        }
    
    def get_is_valid(self, obj):
        return obj.is_valid()
    
    def get_utilisations_restantes(self, obj):
        return obj.nombre_utilisations_max - obj.nombre_utilisations


class UtiliserCodeParrainageSerializer(serializers.Serializer):
    """Serializer pour utiliser un code de parrainage lors de l'inscription"""
    
    code_parrainage = serializers.CharField(max_length=10)
    
    def validate_code_parrainage(self, value):
        """Valider que le code de parrainage existe"""
        try:
            parrain = CustomUser.objects.get(code_parrainage=value)
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Code de parrainage invalide")
    
    def save(self, user):
        """Associer l'utilisateur au parrain"""
        code = self.validated_data['code_parrainage']
        parrain = CustomUser.objects.get(code_parrainage=code)
        
        user.parrain = parrain
        user.date_parrainage = timezone.now()
        user.save()
        
        return user


class StatistiquesParrainageSerializer(serializers.Serializer):
    """Serializer pour les statistiques de parrainage"""
    
    nombre_filleuls_total = serializers.IntegerField()
    nombre_filleuls_actifs = serializers.IntegerField()
    revenus_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    points_total = serializers.IntegerField()
    revenus_ce_mois = serializers.DecimalField(max_digits=10, decimal_places=2)
    filleuls_ce_mois = serializers.IntegerField()
    
    # Évolution mensuelle
    evolution_mensuelle = serializers.ListField(
        child=serializers.DictField()
    )
    
    # Top actions
    top_actions = serializers.ListField(
        child=serializers.DictField()
    )


class ValidationCodeParrainageSerializer(serializers.Serializer):
    """Serializer pour valider un code de parrainage"""
    code_parrainage = serializers.CharField(max_length=20)
    
    def validate_code_parrainage(self, value):
        try:
            user = CustomUser.objects.get(code_parrainage=value)
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Code de parrainage invalide")


class GenerationCodePromoSerializer(serializers.Serializer):
    """Serializer pour générer un code promo"""
    reduction_percent = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        min_value=5.00, 
        max_value=50.00,
        default=10.00
    )
    montant_min = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=10000.00,
        default=50000.00
    )
    duree_jours = serializers.IntegerField(min_value=1, max_value=365, default=30)