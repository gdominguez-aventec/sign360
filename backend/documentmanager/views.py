import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documentmanager.filters import DocumentFilter, DocumentSignFilter
from documentmanager.models import Document, DocumentSign
from documentmanager.serializers import (
    DocumentSerializer,
    DocumentSignCreateSerializer,
    DocumentSignSerializer,
    SendToSignSerializer,
)
from documentmanager.utils.main_utils import (
    delete_document,
    download_document,
    get_default_service,
    upload_document,
)
from documentmanager.utils.pdf_utils import is_pdf
from integrations.outbound.signing.exceptions import SigningApiError
from integrations.outbound.signing.services import create_document_sign_session

logger = logging.getLogger(__name__)

MAX_UPLOAD_MESSAGE = "El fitxer supera la mida màxima permesa."


def _pdf_response(document, pdf_bytes, *, as_attachment):
    filename = document.document_name or f"document-{document.id}.pdf"
    response = HttpResponse(pdf_bytes, content_type=document.content_type or "application/pdf")
    disposition = "attachment" if as_attachment else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{slugify(filename[:-4])}.pdf"'
    return response


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Document.objects.filter(is_active=True)
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DocumentFilter

    @action(detail=True, methods=["get"], url_path="view")
    def view_document(self, request, pk=None):
        """Retorna el fitxer per mostrar-lo incrustat al navegador."""
        document = self.get_object()
        content = download_document(document)
        if content is None:
            return Response(
                {"detail": "No s'ha pogut llegir el document."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return _pdf_response(document, content, as_attachment=False)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        content = download_document(document)
        if content is None:
            return Response(
                {"detail": "No s'ha pogut llegir el document."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return _pdf_response(document, content, as_attachment=True)

    @action(detail=True, methods=["post"], url_path="delete")
    def delete_document(self, request, pk=None):
        document = self.get_object()
        delete_document(document)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentSignViewSet(viewsets.ModelViewSet):
    queryset = DocumentSign.objects.select_related(
        "document_file", "document_file_signed", "created_by"
    ).all()
    serializer_class = DocumentSignSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DocumentSignFilter
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        """
        Alta d'una sol·licitud: puja el PDF i, si `send_now`, obre la sessió de
        signatura tot seguit. Si l'enviament falla, la sol·licitud es conserva en
        estat ERROR perquè es pugui reintentar sense tornar a pujar el fitxer.
        """
        serializer = DocumentSignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        file_obj = data["file"]
        error = self._validate_pdf(file_obj)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        document_sign = DocumentSign.objects.create(
            title=data.get("title") or file_obj.name,
            description=data.get("description", ""),
            otp_name=data["otp_name"],
            otp_email=data["otp_email"],
            otp_phone=data.get("otp_phone", ""),
            created_by=request.user if request.user.is_authenticated else None,
        )

        document = upload_document(
            file_obj,
            "DOCUMENT_SIGN",
            entity_id=document_sign.id,
            entity_token=document_sign.token,
            folder="pending",
            document_name=file_obj.name,
            service=get_default_service(),
            uploaded_by=request.user if request.user.is_authenticated else None,
            content_type="application/pdf",
        )
        document_sign.document_file = document
        document_sign.save(update_fields=["document_file", "updated_at"])

        send_error = None
        if data.get("send_now"):
            try:
                create_document_sign_session(document_sign)
            except SigningApiError as exc:
                logger.warning("No s'ha pogut enviar a firmar el document %s", document_sign.id)
                send_error = str(exc)

        document_sign.refresh_from_db()
        payload = DocumentSignSerializer(document_sign).data
        if send_error:
            payload["send_error"] = send_error
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="send-to-sign")
    def send_to_sign(self, request, pk=None):
        document_sign = self.get_object()
        serializer = SendToSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            session = create_document_sign_session(
                document_sign,
                recipient_name=data.get("otp_name") or None,
                recipient_email=data.get("otp_email") or None,
                recipient_phone=data.get("otp_phone") or None,
                callback_url=data.get("callback_url") or None,
                force=data.get("force", False),
            )
        except SigningApiError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        document_sign.refresh_from_db()
        return Response(
            {
                **DocumentSignSerializer(document_sign).data,
                "session_id": session.session_id,
                "signing_url": session.signing_url,
                "email_sent": session.email_sent,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="view")
    def view_file(self, request, pk=None):
        """Mostra el PDF firmat si n'hi ha; si no, l'original."""
        document_sign = self.get_object()
        document = document_sign.document_file_signed or document_sign.document_file
        return self._file_response(document, as_attachment=False)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document_sign = self.get_object()
        document = document_sign.document_file_signed or document_sign.document_file
        return self._file_response(document, as_attachment=True)

    @action(detail=True, methods=["get"], url_path="download-original")
    def download_original(self, request, pk=None):
        document_sign = self.get_object()
        return self._file_response(document_sign.document_file, as_attachment=True)

    def _file_response(self, document, *, as_attachment):
        if not document:
            return Response(
                {"detail": "Aquesta sol·licitud no té cap document."},
                status=status.HTTP_404_NOT_FOUND,
            )
        content = download_document(document)
        if content is None:
            return Response(
                {"detail": "No s'ha pogut llegir el document."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return _pdf_response(document, content, as_attachment=as_attachment)

    def _validate_pdf(self, file_obj):
        max_size = getattr(settings, "DOCUMENT_MAX_UPLOAD_SIZE", 20 * 1024 * 1024)
        if file_obj.size > max_size:
            return MAX_UPLOAD_MESSAGE
        if not is_pdf(file_obj):
            return "El fitxer ha de ser un PDF."
        return None
