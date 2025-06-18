from django.contrib import admin
from .models import CustomUser
# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'number', 'birthdate', 'is_vendor', 'is_active']
    list_filter = ['is_vendor', 'birthdate',]
    search_fields = ['first_name','last_name', ]
    ordering = ['-date_joined']