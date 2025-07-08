import re
from rest_framework import serializers
from .models import CustomUser, DocumentUtilisateur
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import CustomUser

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Remplacer le champ username par email
    username_field = 'email'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Supprimer le champ username et le remplacer par email
        self.fields.pop('username', None)
        self.fields['email'] = serializers.EmailField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            try:
                # Trouver l'utilisateur par email
                user = CustomUser.objects.get(email=email)
                
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
                }
                
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError('Aucun compte avec cet email.')
        
        raise serializers.ValidationError('Email et mot de passe requis.')
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Ajouter des données personnalisées au token
        token['email'] = user.email
        token['username'] = user.username
        token['is_vendor'] = user.is_vendor
        return token


class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = (
            'id','username', 'email', 'first_name', 'last_name',
            'number', 'birthdate', 'password','reservations',
            'carte_identite','permis_conduire','est_verifie',
            'is_vendor','date_joined','photo_profil','image_banniere'
        )
        ref_name = 'AuthUser'


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'number', 'birthdate', 'password', 'password2', 'is_vendor',
            'est_verifie'
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
        user = CustomUser.objects.create(
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
            is_active=False  # ✅ important
        )
        user.set_password(validated_data['password'])
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
