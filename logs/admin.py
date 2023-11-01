from django.contrib import admin, messages
from .models import Log
class LogAdmin(admin.ModelAdmin):
    ordering = ("-created_at",)
    list_filter = ("method", "user_id")
    search_fields = ("path_info", "ip_address", "user_id")


# Register your models here.
admin.site.register(Log, LogAdmin)
