from django.contrib import admin

# Register your models here.
from .models import Message, Conversation

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['expediteur', 'destinataire', 'objet', 'timestamp', 'lu']
    list_filter = ['timestamp', 'lu', 'archive_expediteur', 'archive_destinataire']
    search_fields = ['objet', 'contenu', 'expediteur__username', 'destinataire__username']
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('Informations du message', {
            'fields': ('expediteur', 'destinataire', 'objet', 'contenu')
        }),
        ('Métadonnées', {
            'fields': ('timestamp', 'lu', 'archive_expediteur', 'archive_destinataire')
        }),
    )

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'cree_le', 'mise_a_jour']
    list_filter = ['cree_le', 'mise_a_jour']
    filter_horizontal = ['participants']