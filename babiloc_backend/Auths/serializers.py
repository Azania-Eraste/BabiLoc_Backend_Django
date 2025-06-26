import re
from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


# Normal login (optionnel, tu peux garder celui par défaut)
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        data['user'] = {
            "username": self.user.username,
            "email": self.user.email,
            "is_vendor": self.user.is_vendor, 
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_vendor'] = user.is_vendor
        token['email'] = user.email
        token['username'] = user.username
        return token

# Auths/serializers.py

class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'number', 'birthdate', 'password','reservations',
            'carte_identite','permis_conduire','est_verifie',
            'is_vendor'
        )
        ref_name = 'AuthUser'

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = (
            'id','username', 'email', 'first_name', 'last_name','date_joined',
            'number', 'birthdate', 'password', 'password2',
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
