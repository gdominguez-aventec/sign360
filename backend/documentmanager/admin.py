from django.contrib import admin

from .models import Document, DocumentSign


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "document_name", "entity", "service", "is_active", "created_at")
    list_filter = ("service", "is_active", "entity")
    search_fields = ("document_name", "entity_token")


@admin.register(DocumentSign)
class DocumentSignAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "token", "status", "otp_email", "signed_at", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "token", "otp_email", "otp_name")
