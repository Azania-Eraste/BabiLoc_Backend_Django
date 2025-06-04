from django.contrib import admin
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'annonce_id', 'status', 
        'date_debut', 'date_fin', 'prix_total', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'date_debut']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'annonce_id', 'status')
        }),
        ('Dates', {
            'fields': ('date_debut', 'date_fin')
        }),
        ('Prix et message', {
            'fields': ('prix_total', 'message')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )