from django.contrib import admin
from .forms import BienForm
from .models import Reservation, Favori, Bien, Type_Bien, Tarif, Media, Avis

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'bien', 'status',  # Changer annonce_id en bien
        'date_debut', 'date_fin', 'prix_total', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'date_debut']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'bien', 'status')  # Changer annonce_id en bien
        }),
        ('Dates', {
            'fields': ('date_debut', 'date_fin')
        }),
        ('Prix et message', {
            'fields': ('type_tarif', 'message')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'bien', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'bien__nom']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

# Add missing model registrations
@admin.register(Bien)
class BienAdmin(admin.ModelAdmin):
    form = BienForm
    list_display = ['id', 'nom', 'ville', 'owner', 'disponibility', 'type_bien']
    list_filter = ['disponibility', 'type_bien', 'ville', 'created_at']
    search_fields = ['nom', 'description', 'ville', 'owner__username']
    ordering = ['-created_at']

@admin.register(Type_Bien)
class TypeBienAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'created_at']
    search_fields = ['nom', 'description']

@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    list_display = ['id', 'type_tarif', 'prix', 'bien', 'created_at']
    list_filter = ['created_at']
    search_fields = ['type_tarif', 'bien__nom']

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'bien', 'image']
    list_filter = ['bien']

@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'bien', 'note', 'recommande', 
        'est_valide', 'created_at', 'has_response'
    ]
    list_filter = [
        'note', 'recommande', 'est_valide', 'created_at',
        'note_proprete', 'note_communication'
    ]
    search_fields = [
        'user__username', 'user__email', 'bien__nom', 
        'commentaire', 'reponse_proprietaire'
    ]
    readonly_fields = ['created_at', 'updated_at', 'note_moyenne_detaillee']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'bien', 'reservation', 'est_valide')
        }),
        ('Évaluation', {
            'fields': (
                'note', 'commentaire', 'recommande',
                'note_proprete', 'note_communication',
                'note_emplacement', 'note_rapport_qualite_prix'
            )
        }),
        ('Réponse du propriétaire', {
            'fields': ('reponse_proprietaire', 'date_reponse'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'note_moyenne_detaillee'),
            'classes': ('collapse',)
        }),
    )
    
    def has_response(self, obj):
        return bool(obj.reponse_proprietaire)
    has_response.boolean = True
    has_response.short_description = "A une réponse"