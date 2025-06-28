from django.contrib import admin
from .forms import BienForm
from .models import Reservation, Favori, Bien, Type_Bien, Tarif, Media, DisponibiliteHebdo

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'annonce_id', 'status',  # Changé 'annonce_id_id' en 'annonce_id'
        'date_debut', 'date_fin', 'prix_total', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'date_debut']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'annonce_id', 'status')  # Changé 'annonce_id_id' en 'annonce_id'
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

@admin.register(DisponibiliteHebdo)
class DisponibiliteHebdoAdmin(admin.ModelAdmin):
    list_display = ('bien', 'jours', )
    list_filter = ('bien',)

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