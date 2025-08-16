from django.contrib import admin
from .forms import BienForm
from .models import Reservation, Ville,Favori, Bien, Type_Bien, Tarif, Media, Avis, Facture, DisponibiliteHebdo, TagBien, Document

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


@admin.register(TagBien)
class TagBienAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'iconName','created_at']
    search_fields = ['nom']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'iconName')
        }),
    )

@admin.register(Ville)
class VilleAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'pays', 'created_at']
    search_fields = ['nom', 'pays']
    ordering = ['-created_at']

    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'pays')
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
    list_display = ('bien', 'jours', 'heure_debut', 'heure_fin')
    list_filter = ('bien', 'heure_debut', 'heure_fin')
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('bien', 'jours')
        }),
        ('Horaires', {
            'fields': ('heure_debut', 'heure_fin')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Bien)
class BienAdmin(admin.ModelAdmin):
    form = BienForm
    list_display = ['id', 'nom', 'ville', 'lieu', 'owner', 'disponibility', 'type_bien']
    list_filter = ['disponibility', 'type_bien', 'ville', 'created_at', 'carburant', 'transmission']
    search_fields = ['nom', 'description', 'ville__nom', 'lieu', 'owner__username', 'marque', 'modele']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'vues']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'description', 'type_bien', 'ville', 'lieu', 'owner', 'disponibility', 'est_verifie')
        }),
        ('Spécifications véhicule', {
            'fields': ('marque', 'modele', 'plaque', 'nb_places', 'carburant', 'transmission', 'chauffeur', 'prix_chauffeur'),
            'classes': ('collapse',),
            'description': 'Champs spécifiques aux véhicules'
        }),
        ('Spécifications immobilier', {
            'fields': ('nb_chambres', 'nb_douches'),
            'classes': ('collapse',),
            'description': 'Champs spécifiques aux biens immobiliers'
        }),
        ('Équipements et services', {
            'fields': ('has_piscine', 'has_wifi', 'has_parking', 'has_kitchen', 'has_security', 'has_garden'),
            'classes': ('collapse',),
            'description': 'Équipements disponibles pour les biens immobiliers'
        }),
        ('Métadonnées', {
            'fields': ('noteGlobale', 'vues', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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
    list_display = ['id', 'bien', 'type_media', 'image']
    list_filter = ['bien', 'type_media']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('bien', 'type_media', 'image')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'bien', 'nom', 'type', 'has_file', 'has_image', 'date_upload']
    list_filter = ['type', 'date_upload', 'bien']
    search_fields = ['nom', 'bien__nom', 'bien__owner__username']
    readonly_fields = ['created_at', 'updated_at', 'date_upload']
    
    def has_file(self, obj):
        return bool(obj.fichier)
    has_file.boolean = True
    has_file.short_description = "Fichier"
    
    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Image"
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('bien', 'nom', 'type')
        }),
        ('Fichiers', {
            'fields': ('fichier', 'image')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'date_upload'),
            'classes': ('collapse',)
        }),
    )

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

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = [
        'numero_facture', 'client_nom', 'hote_nom', 'montant_ttc',
        'statut', 'date_emission', 'date_paiement'
    ]
    list_filter = ['statut', 'type_facture', 'date_emission']
    search_fields = [
        'numero_facture', 'client_nom', 'client_email',
        'hote_nom', 'hote_email'
    ]
    readonly_fields = [
        'numero_facture', 'montant_ht', 'montant_tva', 'montant_ttc',
        'commission_plateforme', 'montant_net_hote', 'created_at', 'updated_at'
    ]
    ordering = ['-date_emission']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('numero_facture', 'type_facture', 'reservation', 'paiement', 'statut')
        }),
        ('Client', {
            'fields': ('client_nom', 'client_email', 'client_telephone', 'client_adresse')
        }),
        ('Hôte', {
            'fields': ('hote_nom', 'hote_email', 'hote_telephone')
        }),
        ('Montants', {
            'fields': (
                'montant_ht', 'tva_taux', 'montant_tva', 'montant_ttc',
                'commission_plateforme', 'montant_net_hote'
            )
        }),
        ('Dates', {
            'fields': ('date_emission', 'date_echeance', 'date_paiement')
        }),
        ('Fichier', {
            'fields': ('fichier_pdf',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['regenerer_pdf', 'envoyer_email']
    
    def regenerer_pdf(self, request, queryset):
        """Action pour régénérer les PDFs"""
        for facture in queryset:
            facture.generer_pdf()
        self.message_user(request, f"{queryset.count()} facture(s) régénérée(s)")
    
    regenerer_pdf.short_description = "Régénérer les PDFs"
    
    def envoyer_email(self, request, queryset):
        """Action pour envoyer les factures par email"""
        sent = 0
        for facture in queryset:
            if facture.envoyer_par_email():
                sent += 1
        self.message_user(request, f"{sent} facture(s) envoyée(s) par email")
    
    envoyer_email.short_description = "Envoyer par email"