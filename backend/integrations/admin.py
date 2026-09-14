from django.contrib import admin

from .models import IntegrationRequestLog, SigningSession


@admin.register(IntegrationRequestLog)
class IntegrationRequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "direction", "method", "endpoint", "status_code", "success", "created_at")
    list_filter = ("provider", "direction", "success")
    search_fields = ("endpoint", "object_id", "error_message")


@admin.register(SigningSession)
class SigningSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "session_id", "signer", "status", "recipient_email", "signed_at")
    list_filter = ("status",)
    search_fields = ("session_id", "external_reference", "recipient_email")
