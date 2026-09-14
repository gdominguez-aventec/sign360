import logging

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documentmanager.filters import DocumentFilter, DocumentSignFilter
from documentmanager.models import (
    Document,
    DocumentSign,
    DocumentSignDocument,
    DocumentSignSigner,
)
from documentmanager.serializers import (
    DocumentSerializer,
    DocumentSignCreateSerializer,
    DocumentSignDocumentSerializer,
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
from integrations.outbound.signing.services import create_signer_session, send_next_signer

logger = logging.getLogger(__name__)


def _pdf_response(document, pdf_bytes, *, as_attachment):
    filename = document.document_name or f"document-{document.id}.pdf"
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    response = HttpResponse(pdf_bytes, content_type=document.content_type or "application/pdf")
    disposition = "attachment" if as_attachment else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{slugify(stem)}.pdf"'
    return response


def _serve(document, *, as_attachment):
    if not document:
        return Response({"detail": "Document no trobat."}, status=status.HTTP_404_NOT_FOUND)
    content = download_document(document)
    if content is None:
        return Response(
            {"detail": "No s'ha pogut llegir el document."}, status=status.HTTP_404_NOT_FOUND
        )
    return _pdf_response(document, content, as_attachment=as_attachment)


def _validate_pdf(file_obj):
    max_size = getattr(settings, "DOCUMENT_MAX_UPLOAD_SIZE", 20 * 1024 * 1024)
    if file_obj.size > max_size:
        return f"El fitxer «{file_obj.name}» supera la mida màxima permesa."
    if not is_pdf(file_obj):
        return f"El fitxer «{file_obj.name}» no és un PDF."
    return None


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """Accés directe als fitxers, inclosa qualsevol versió de la cadena."""

    queryset = Document.objects.filter(is_active=True)
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DocumentFilter

    @action(detail=True, methods=["get"], url_path="view")
    def view_document(self, request, pk=None):
        return _serve(self.get_object(), as_attachment=False)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        return _serve(self.get_object(), as_attachment=True)

    @action(detail=True, methods=["post"], url_path="delete")
    def delete_document(self, request, pk=None):
        delete_document(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentSignDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Un document dins d'una sol·licitud. Permet baixar-ne tant la versió actual
    com l'original tal com ens el van passar.
    """

    queryset = DocumentSignDocument.objects.select_related(
        "original_document", "current_document", "document_sign"
    ).prefetch_related("signatures__signer")
    serializer_class = DocumentSignDocumentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["document_sign"]

    @action(detail=True, methods=["get"], url_path="view")
    def view_current(self, request, pk=None):
        return _serve(self.get_object().current_document, as_attachment=False)

    @action(detail=True, methods=["get"], url_path="download")
    def download_current(self, request, pk=None):
        return _serve(self.get_object().current_document, as_attachment=True)

    @action(detail=True, methods=["get"], url_path="view-original")
    def view_original(self, request, pk=None):
        return _serve(self.get_object().original_document, as_attachment=False)

    @action(detail=True, methods=["get"], url_path="download-original")
    def download_original(self, request, pk=None):
        return _serve(self.get_object().original_document, as_attachment=True)


class DocumentSignViewSet(viewsets.ModelViewSet):
    queryset = (
        DocumentSign.objects.select_related("created_by")
        .prefetch_related(
            "signers",
            "documents__original_document",
            "documents__current_document",
            "documents__signatures__signer",
        )
        .all()
    )
    serializer_class = DocumentSignSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DocumentSignFilter
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        """
        Alta d'una sol·licitud amb N documents i M signants. Si `send_now`,
        s'obre la sessió del primer signant de la cadena; si l'enviament falla,
        la sol·licitud es conserva perquè es pugui reintentar sense tornar a
        pujar els fitxers.
        """
        serializer = DocumentSignCreateSerializer(
            data={
                "files": request.FILES.getlist("files"),
                "title": request.data.get("title", ""),
                "description": request.data.get("description", ""),
                "signers": request.data.get("signers", ""),
                "send_now": request.data.get("send_now", False),
            }
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        for file_obj in validated["files"]:
            error = _validate_pdf(file_obj)
            if error:
                return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None

        with transaction.atomic():
            document_sign = DocumentSign.objects.create(
                title=validated.get("title") or validated["files"][0].name,
                description=validated.get("description", ""),
                created_by=user,
            )

            for order, file_obj in enumerate(validated["files"], start=1):
                document = upload_document(
                    file_obj,
                    "DOCUMENT_SIGN",
                    entity_id=document_sign.id,
                    entity_token=document_sign.token,
                    folder="original",
                    document_name=file_obj.name,
                    service=get_default_service(),
                    uploaded_by=user,
                    content_type="application/pdf",
                )
                DocumentSignDocument.objects.create(
                    document_sign=document_sign,
                    order=order,
                    original_document=document,
                    # Mentre ningú no hagi firmat, la versió actual és l'original.
                    current_document=document,
                )

            for order, signer in enumerate(validated["signers"], start=1):
                DocumentSignSigner.objects.create(
                    document_sign=document_sign,
                    order=order,
                    name=signer["name"],
                    email=signer["email"],
                    phone=signer.get("phone", ""),
                )

        send_error = None
        if validated.get("send_now"):
            try:
                send_next_signer(document_sign)
            except SigningApiError as exc:
                logger.warning("No s'ha pogut enviar a firmar la sol·licitud %s", document_sign.id)
                send_error = str(exc)

        document_sign.refresh_from_db()
        payload = self.get_serializer(document_sign).data
        if send_error:
            payload["send_error"] = send_error
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="send-to-sign")
    def send_to_sign(self, request, pk=None):
        document_sign = self.get_object()
        serializer = SendToSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        callback_url = data.get("callback_url") or None
        force = data.get("force", False)

        try:
            if data.get("signer"):
                signer = document_sign.signers.filter(id=data["signer"]).first()
                if not signer:
                    return Response(
                        {"detail": "Aquest signant no pertany a la sol·licitud."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                session = create_signer_session(signer, callback_url=callback_url, force=force)
            else:
                session = send_next_signer(
                    document_sign, callback_url=callback_url, force=force
                )
        except SigningApiError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        document_sign.refresh_from_db()
        return Response(
            {
                **self.get_serializer(document_sign).data,
                "session_id": session.session_id,
                "signing_url": session.signing_url,
                "email_sent": session.email_sent,
                "sent_to": session.recipient_email,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        document_sign = self.get_object()
        return Response(
            DocumentSignDocumentSerializer(document_sign.documents.all(), many=True).data
        )
