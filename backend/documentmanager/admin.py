from django.contrib import admin

from .models import (
    Document,
    DocumentSign,
    DocumentSignDocument,
    DocumentSignSignature,
    DocumentSignSigner,
)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document_name",
        "entity",
        "version",
        "parent_document",
        "service",
        "is_active",
        "created_at",
    )
    list_filter = ("service", "is_active", "entity")
    search_fields = ("document_name", "entity_token")


class DocumentSignDocumentInline(admin.TabularInline):
    model = DocumentSignDocument
    extra = 0
    raw_id_fields = ("original_document", "current_document")


class DocumentSignSignerInline(admin.TabularInline):
    model = DocumentSignSigner
    extra = 0


@admin.register(DocumentSign)
class DocumentSignAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "token", "status", "signed_at", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "token", "signers__email", "signers__name")
    inlines = [DocumentSignDocumentInline, DocumentSignSignerInline]


@admin.register(DocumentSignSignature)
class DocumentSignSignatureAdmin(admin.ModelAdmin):
    list_display = ("id", "signer", "sign_document", "document", "created_at")
    raw_id_fields = ("signer", "sign_document", "document")
