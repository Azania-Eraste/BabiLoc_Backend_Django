from django.contrib import admin
from .models import CustomUser, DocumentUtilisateur, HistoriqueParrainage, CodePromoParrainage
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q

# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'number', 'birthdate','code_parrainage', 'is_vendor', 'is_active']
    list_filter = ['is_vendor', 'birthdate',]
    search_fields = ['first_name','last_name', ]
    ordering = ['-date_joined']

@admin.register(DocumentUtilisateur)
class DocumentUtilisateurAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'utilisateur', 'type_document', 'statut_verification',
        'structure_type', 'date_upload', 'date_verification', 'is_expired', 'is_vendor_request'
    ]
    list_filter = [
        'type_document', 'statut_verification', 'structure_type', 'date_upload', 'date_verification'
    ]
    search_fields = [
        'utilisateur__username', 'utilisateur__email', 'nom', 'agence_nom'
    ]
    readonly_fields = ['date_upload', 'date_verification']
    ordering = ['-date_upload']
    
    # ✅ Actions personnalisées pour les demandes vendor
    actions = ['approuver_demande_vendor', 'refuser_demande_vendor', 'marquer_comme_verifie']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('utilisateur', 'nom', 'type_document', 'structure_type')
        }),
        ('Informations entreprise', {
            'fields': ('agence_nom', 'agence_adresse', 'representant_telephone'),
            'classes': ('collapse',)
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
    
    # ✅ Nouvelle méthode pour identifier les demandes vendor
    def is_vendor_request(self, obj):
        """Indique si c'est une demande de vendor"""
        return "Demande vendor" in obj.nom
    is_vendor_request.boolean = True
    is_vendor_request.short_description = "Demande Vendor"
    
    # ✅ Action pour approuver les demandes vendor
    def approuver_demande_vendor(self, request, queryset):
        """Approuver les demandes de vendor sélectionnées"""
        approved_count = 0
        
        for document in queryset:
            if "Demande vendor" in document.nom and document.statut_verification == 'en_attente':
                # Marquer le document comme approuvé
                document.statut_verification = 'approuve'
                document.moderateur = request.user
                document.save()
                
                # Activer le statut vendor de l'utilisateur
                user = document.utilisateur
                if not user.is_vendor:
                    user.is_vendor = True
                    user.est_verifie = True
                    user.save()
                    approved_count += 1
                    
                    # Envoyer email de confirmation
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings
                        
                        send_mail(
                            subject='🎉 Demande vendor approuvée - BabiLoc',
                            message=f'Félicitations {user.get_full_name() or user.username} !\n\nVotre demande pour devenir propriétaire/hôte a été approuvée.\n\nVous pouvez maintenant publier vos biens sur BabiLoc.\n\nL\'équipe BabiLoc',
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[user.email],
                            fail_silently=True
                        )
                    except Exception as e:
                        pass  # Email non critique
        
        self.message_user(request, f"{approved_count} demande(s) vendor approuvée(s)")
    
    approuver_demande_vendor.short_description = "✅ Approuver les demandes vendor sélectionnées"
    
    # ✅ Action pour refuser les demandes vendor
    def refuser_demande_vendor(self, request, queryset):
        """Refuser les demandes de vendor sélectionnées"""
        refused_count = 0
        
        for document in queryset:
            if "Demande vendor" in document.nom and document.statut_verification == 'en_attente':
                # Marquer le document comme refusé
                document.statut_verification = 'refuse'
                document.moderateur = request.user
                document.commentaire_moderateur = "Demande vendor refusée par l'administration"
                document.save()
                refused_count += 1
                
                # Envoyer email de refus
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    user = document.utilisateur
                    send_mail(
                        subject='❌ Demande vendor refusée - BabiLoc',
                        message=f'Bonjour {user.get_full_name() or user.username},\n\nNous regrettons de vous informer que votre demande pour devenir propriétaire/hôte a été refusée.\n\nRaison: Documents non conformes ou incomplets.\n\nVous pouvez soumettre une nouvelle demande avec des documents mis à jour.\n\nL\'équipe BabiLoc',
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=True
                    )
                except Exception as e:
                    pass  # Email non critique
        
        self.message_user(request, f"{refused_count} demande(s) vendor refusée(s)")
    
    refuser_demande_vendor.short_description = "❌ Refuser les demandes vendor sélectionnées"
    
    # ✅ Action pour marquer comme vérifié (documents normaux)
    def marquer_comme_verifie(self, request, queryset):
        """Marquer les documents comme vérifiés"""
        updated = queryset.update(
            statut_verification='approuve',
            moderateur=request.user
        )
        self.message_user(request, f"{updated} document(s) marqué(s) comme vérifié(s)")
    
    marquer_comme_verifie.short_description = "✅ Marquer comme vérifié"
    
    # ✅ Filtres personnalisés
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('utilisateur', 'moderateur')
    
    # ✅ Méthodes d'affichage enrichies
    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        # Ajouter un filtre personnalisé pour les demandes vendor
        filters.append(VendorRequestFilter)
        return filters

# ✅ Filtre personnalisé pour les demandes vendor
class VendorRequestFilter(admin.SimpleListFilter):
    title = 'Type de demande'
    parameter_name = 'vendor_request'
    
    def lookups(self, request, model_admin):
        return (
            ('vendor', 'Demandes Vendor'),
            ('documents', 'Documents normaux'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'vendor':
            return queryset.filter(nom__icontains='Demande vendor')
        elif self.value() == 'documents':
            return queryset.exclude(nom__icontains='Demande vendor')
        return queryset

# ✅ Admin proxy pour les demandes vendor uniquement
class DemandeVendor(DocumentUtilisateur):
    class Meta:
        proxy = True
        verbose_name = "Demande Vendor"
        verbose_name_plural = "Demandes Vendor"

@admin.register(DemandeVendor)
class DemandeVendorAdmin(admin.ModelAdmin):
    """Interface dédiée pour gérer uniquement les demandes vendor"""
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            nom__icontains='Demande vendor'
        ).select_related('utilisateur')
    
    list_display = [
        'id', 'utilisateur_info', 'structure_type', 'agence_info', 
        'statut_verification', 'date_upload', 'documents_count'
    ]
    list_filter = ['statut_verification', 'structure_type', 'date_upload']
    search_fields = ['utilisateur__username', 'utilisateur__email', 'agence_nom']
    ordering = ['-date_upload']
    
    actions = ['approuver_demandes', 'refuser_demandes']
    
    def utilisateur_info(self, obj):
        """Informations utilisateur complètes"""
        user = obj.utilisateur
        return format_html(
            '<strong>{}</strong><br/>'
            '📧 {}<br/>'
            '📱 {}',
            user.get_full_name() or user.username,
            user.email,
            user.number or 'Non renseigné'
        )
    utilisateur_info.short_description = "Utilisateur"
    
    def agence_info(self, obj):
        """Informations agence/société"""
        if obj.structure_type == 'particulier':
            return "Particulier"
        return format_html(
            '<strong>{}</strong><br/>'
            '📍 {}<br/>'
            '📞 {}',
            obj.agence_nom or 'Non renseigné',
            obj.agence_adresse or 'Non renseigné',
            obj.representant_telephone or 'Non renseigné'
        )
    agence_info.short_description = "Informations Structure"
    
    def documents_count(self, obj):
        """Nombre de documents associés à cette demande"""
        count = DocumentUtilisateur.objects.filter(
            utilisateur=obj.utilisateur,
            nom__icontains='Demande vendor'
        ).count()
        return f"{count} document(s)"
    documents_count.short_description = "Documents"
    
    def approuver_demandes(self, request, queryset):
        """Approuver les demandes sélectionnées"""
        approved = 0
        for demande in queryset:
            if demande.statut_verification == 'en_attente':
                # Approuver tous les documents de cette demande
                DocumentUtilisateur.objects.filter(
                    utilisateur=demande.utilisateur,
                    nom__icontains='Demande vendor'
                ).update(
                    statut_verification='approuve',
                    moderateur=request.user
                )
                
                # Activer le vendor
                user = demande.utilisateur
                user.is_vendor = True
                user.est_verifie = True
                user.save()
                approved += 1
        
        self.message_user(request, f"{approved} demande(s) approuvée(s)")
    approuver_demandes.short_description = "✅ Approuver les demandes"
    
    def refuser_demandes(self, request, queryset):
        """Refuser les demandes sélectionnées"""
        refused = 0
        for demande in queryset:
            if demande.statut_verification == 'en_attente':
                # Refuser tous les documents de cette demande
                DocumentUtilisateur.objects.filter(
                    utilisateur=demande.utilisateur,
                    nom__icontains='Demande vendor'
                ).update(
                    statut_verification='refuse',
                    moderateur=request.user,
                    commentaire_moderateur="Demande refusée par l'administration"
                )
                refused += 1
        
        self.message_user(request, f"{refused} demande(s) refusée(s)")
    refuser_demandes.short_description = "❌ Refuser les demandes"