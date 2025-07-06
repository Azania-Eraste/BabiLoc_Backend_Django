from django.contrib import admin
from .models import CustomUser, DocumentUtilisateur
# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'number', 'birthdate', 'is_vendor', 'is_active']
    list_filter = ['is_vendor', 'birthdate',]
    search_fields = ['first_name','last_name', ]
    ordering = ['-date_joined']

@admin.register(DocumentUtilisateur)
class DocumentUtilisateurAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'utilisateur', 'type_document', 'statut_verification',
        'date_upload', 'date_verification', 'is_expired'
    ]
    list_filter = [
        'type_document', 'statut_verification', 'date_upload', 'date_verification'
    ]
    search_fields = [
        'utilisateur__username', 'utilisateur__email', 'nom'
    ]
    readonly_fields = ['date_upload', 'date_verification']
    ordering = ['-date_upload']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('utilisateur', 'nom', 'type_document')
        }),
        ('Fichier', {
            'fields': ('fichier', 'image')
        }),
        ('Vérification', {
            'fields': ('statut_verification', 'commentaire_moderateur', 'date_expiration')
        }),
        ('Métadonnées', {
            'fields': ('date_upload', 'date_verification', 'moderateur'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = "Expiré"