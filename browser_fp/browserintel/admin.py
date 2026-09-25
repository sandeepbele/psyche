from django.contrib import admin
from .models import FingerprintData

class FingerprintDataAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'user_identifier','access_time','stable_fp','ip_address','browser','device','is_bot','bot_type')
    ordering = ('-access_time',)
    search_fields = ('request_id', 'user_identifier', 'access_time', 'is_bot')
    list_filter = ('is_bot', 'access_time')

admin.site.register(FingerprintData, FingerprintDataAdmin)
