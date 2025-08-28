from django.contrib import admin
from .models import ChatRoom, ChatMessage

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'property_name', 'user', 'host', 'status', 
        'reservation', 'created_at', 'last_message_at'
    ]
    list_filter = ['status', 'created_at', 'last_message_at']
    search_fields = [
        'property_name', 'user__username', 'host__username',
        'reservation__id', 'supabase_id'
    ]
    readonly_fields = ['created_at', 'last_message_at', 'supabase_id']
    ordering = ['-last_message_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('reservation', 'user', 'host', 'property_name', 'status')
        }),
        ('Supabase', {
            'fields': ('supabase_id',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'last_message_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'host', 'reservation')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'chat_room', 'sender', 'message_type', 
        'is_read', 'created_at', 'short_message'
    ]
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = [
        'message', 'sender__username', 'chat_room__property_name'
    ]
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('chat_room', 'sender', 'message_type', 'is_read')
        }),
        ('Contenu', {
            'fields': ('message',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def short_message(self, obj):
        """Affiche un aperçu du message"""
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    
    short_message.short_description = "Aperçu du message"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('chat_room', 'sender')

    # Actions personnalisées
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Marquer les messages comme lus"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} message(s) marqué(s) comme lu(s)")
    
    mark_as_read.short_description = "Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        """Marquer les messages comme non lus"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} message(s) marqué(s) comme non lu(s)")
    
    mark_as_unread.short_description = "Marquer comme non lu"
