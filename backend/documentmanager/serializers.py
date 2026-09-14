from rest_framework import serializers

from .models import Document, DocumentSign


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
        # serveixen sempre a través de `view_document` / `download`.
        read_only_fields = fields


class DocumentSignSerializer(serializers.ModelSerializer):
    document_file_detail = DocumentSerializer(source="document_file", read_only=True)
    document_file_signed_detail = DocumentSerializer(
        source="document_file_signed", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = DocumentSign
        fields = [
            "id",
            "created_at",
            "updated_at",
            "token",
            "title",
            "description",
            "document_file",
            "document_file_detail",
            "document_file_signed",
            "document_file_signed_detail",
            "signed_at",
            "status",
            "status_label",
            "error_report",
            "otp_name",
            "otp_email",
            "otp_phone",
            "created_by",
            "created_by_username",
        ]
        read_only_fields = [
            "token",
            "document_file",
            "document_file_signed",
            "signed_at",
            "status",
            "error_report",
            "created_by",
        ]


class DocumentSignCreateSerializer(serializers.Serializer):
    """Alta d'una sol·licitud de signatura: el PDF arriba com a multipart."""

    file = serializers.FileField()
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    otp_name = serializers.CharField()
    otp_email = serializers.EmailField()
    otp_phone = serializers.CharField(required=False, allow_blank=True)
    send_now = serializers.BooleanField(required=False, default=False)


class SendToSignSerializer(serializers.Serializer):
    """Sobreescriptura opcional de les dades del signant en enviar a firmar."""

    otp_name = serializers.CharField(required=False, allow_blank=True)
    otp_email = serializers.EmailField(required=False, allow_blank=True)
    otp_phone = serializers.CharField(required=False, allow_blank=True)
    callback_url = serializers.URLField(required=False, allow_blank=True)
    force = serializers.BooleanField(required=False, default=False)
