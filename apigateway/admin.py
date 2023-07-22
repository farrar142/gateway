from django.contrib import admin, messages

from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import redirect, get_object_or_404

# Register your models here.

from .models import (
    AdminApi,
    Api,
    BasicApi,
    DefaultApi,
    ETCApi,
    KeyApi,
    Upstream,
    Target,
)
from .plugins import Consumer

from django.urls import reverse
from django.utils.safestring import mark_safe


class BaseTabluarInline(admin.TabularInline):
    can_delete = True
    extra = 0


class TargetInline(BaseTabluarInline):
    model = Target

    fields = ("scheme", "host", "weight", "enabled", "toggle")
    readonly_fields = ("toggle",)

    def toggle(self, obj: Target):
        str(obj)
        text = "Deactivate" if obj.enabled else "Activate"
        url = reverse(
            "admin:admin_toggle_enabled",
            args=[obj.pk],
        )
        return mark_safe(f'<a href="{url}">{text}</a>')


class APIInline(BaseTabluarInline):
    model = DefaultApi
    exclude = ("consumers",)
    ordering = ("plugin", "request_path")


class APIAdminInline(APIInline):
    model = AdminApi
    verbose_name = "admin api"
    verbose_name_plural = "Admin API"


class APIKeyInline(APIInline):
    model = KeyApi
    verbose_name = "key api"
    verbose_name_plural = "Key API"


class APIBasicInline(APIInline):
    model = BasicApi
    verbose_name = "basic api"
    verbose_name_plural = "Basic API"


class APIETCInline(APIInline):
    model = ETCApi
    verbose_name = "etc api"
    verbose_name_plural = "ETC API"


class APIAdmin(admin.ModelAdmin):
    ordering = ("upstream", "request_path")
    list_filter = ("upstream", "plugin")
    list_per_page = 10


class UpstreamAdmin(admin.ModelAdmin):
    inlines = [
        TargetInline,
        APIInline,
        APIAdminInline,
        APIKeyInline,
        APIBasicInline,
        APIETCInline,
    ]
    readonly_fields = ("total_weight",)
    search_fields = ("alias",)
    fields = (
        "total_weight",
        "alias",
        "scheme",
        "host",
        "weight",
        "load_balance",
        "retries",
        "timeout",
    )
    list_display = (
        "__str__",
        "host",
        "retries",
        "timeout",
        "total_apis",
        "total_targets",
    )
    list_per_page = 10

    def get_queryset(self, request):
        from django.db import models

        queryset = super(UpstreamAdmin, self).get_queryset(request)
        queryset = (
            queryset.prefetch_related("targets", "api_set", "api_set__consumers")
            .annotate(apis_count=models.Count("api_set"))
            .order_by("-apis_count")
        )
        return queryset

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)


class TargetAdmin(admin.ModelAdmin):
    ordering = ("upstream",)
    list_filter = ("upstream",)
    list_display = ("__str__", "enabled", "toggle_button")

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/toggle-enabled",
                self.toggle_enabled,
                name="admin_toggle_enabled",
            ),
        ]
        return my_urls + urls

    def toggle_enabled(self, request, pk):
        # ...
        context = dict(
            # Include common variables for rendering the admin template.
            self.admin_site.each_context(request),
            # Anything else you want in the context...
        )

        # Get the scenario to activate
        target = get_object_or_404(Target, pk=pk)
        # It is already activated
        target.enabled = not target.enabled
        target.save()
        result = "Activated" if target.enabled else "Deactivated"
        msg = f"{result} Target '{target}'"
        self.message_user(request, msg, level=messages.INFO)
        return redirect(request.META.get("HTTP_REFERER"))


# Register your models here.
admin.site.register(Upstream, UpstreamAdmin)
admin.site.register(Api, APIAdmin)
admin.site.register(Consumer)
# admin.site.register(Upstream)
admin.site.register(Target, TargetAdmin)
