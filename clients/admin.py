from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'email', 'phone', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'company', 'email']
    readonly_fields = ['created_at', 'updated_at']


admin.site.site_header = 'Nexo · Administración'
admin.site.site_title = 'Nexo CRM'
