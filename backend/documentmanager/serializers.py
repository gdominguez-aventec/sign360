import json

from django.conf import settings
from rest_framework import serializers

from .models import (
    Document,
    DocumentSign,
    DocumentSignDocument,
    DocumentSignSignature,
    DocumentSignSigner,
)


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "created_at",
            "updated_at",
            "date",
            "entity",
            "entity_id",
            "entity_token",
            "folder",
            "document_name",
            "content_type",
            "size",
            "version",
            "parent_document",
            "service",
            "is_active",
            "uploaded_by",
            "uploaded_by_username",
        ]
        # `location` no s'exposa mai: és una ruta del servidor i els fitxers es
        # serveixen sempre a través de `view` / `download`.
        read_only_fields = fields


class DocumentSignSignatureSerializer(serializers.ModelSerializer):
    signer_name = serializers.CharField(source="signer.name", read_only=True)
    signer_order = serializers.IntegerField(source="signer.order", read_only=True)
    document_detail = DocumentSerializer(source="document", read_only=True)

    class Meta:
        model = DocumentSignSignature
        fields = [
            "id",
            "signer",
            "signer_name",
            "signer_order",
            "document",
            "document_detail",
            "created_at",
        ]
        read_only_fields = fields


class DocumentSignDocumentSerializer(serializers.ModelSerializer):
    original_document_detail = DocumentSerializer(source="original_document", read_only=True)
    current_document_detail = DocumentSerializer(source="current_document", read_only=True)
    signatures = DocumentSignSignatureSerializer(many=True, read_only=True)
    is_signed = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentSignDocument
        fields = [
            "id",
            "order",
            "original_document",
            "original_document_detail",
            "current_document",
            "current_document_detail",
            "is_signed",
            "signatures",
        ]
        read_only_fields = fields


class DocumentSignSignerSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DocumentSignSigner
        fields = [
            "id",
            "order",
            "name",
            "email",
            "phone",
            "status",
            "status_label",
            "signed_at",
            "error_report",
        ]
        read_only_fields = ["status", "status_label", "signed_at", "error_report"]


class DocumentSignSerializer(serializers.ModelSerializer):
    documents = DocumentSignDocumentSerializer(many=True, read_only=True)
    signers = DocumentSignSignerSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    documents_count = serializers.IntegerField(source="documents.count", read_only=True)
    signers_count = serializers.IntegerField(source="signers.count", read_only=True)
    next_signer = serializers.SerializerMethodField()

    class Meta:
        model = DocumentSign
        fields = [
            "id",
            "created_at",
            "updated_at",
            "token",
            "title",
            "description",
            "status",
            "status_label",
            "error_report",
            "signed_at",
            "created_by",
            "created_by_username",
            "documents",
            "documents_count",
            "signers",
            "signers_count",
            "next_signer",
        ]
        read_only_fields = fields

    def get_next_signer(self, obj):
        signer = obj.next_pending_signer()
        return DocumentSignSignerSerializer(signer).data if signer else None


class SignerInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, default="")


class DocumentSignCreateSerializer(serializers.Serializer):
    """
    Alta d'una sol·licitud. Arriba com a multipart: un o més PDF al camp
    `files`, i els signants com a JSON al camp `signers` (una cadena, perquè
    dins d'un multipart no hi caben estructures).
    """

    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    signers = serializers.CharField()
    send_now = serializers.BooleanField(required=False, default=False)

    def validate_signers(self, value):
        try:
            raw = json.loads(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("El camp `signers` ha de ser JSON vàlid.")

        if not isinstance(raw, list) or not raw:
            raise serializers.ValidationError("Cal com a mínim un signant.")

        # La signatura encadenada està implementada però desactivada per
        # configuració; mentre ho estigui, només s'admet un signant.
        if len(raw) > 1 and not getattr(settings, "MULTI_SIGNER_ENABLED", False):
            raise serializers.ValidationError(
                "La signatura per part de més d'una persona està desactivada."
            )

        serializer = SignerInputSerializer(data=raw, many=True)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class SendToSignSerializer(serializers.Serializer):
    """
    Enviament al signant de torn. `signer` permet forçar-ne un de concret
    (reintent d'un torn caducat o erroni); si no s'indica, s'agafa el següent
    de la cadena que encara no ha firmat.
    """

    signer = serializers.IntegerField(required=False)
    callback_url = serializers.URLField(required=False, allow_blank=True)
    force = serializers.BooleanField(required=False, default=False)
