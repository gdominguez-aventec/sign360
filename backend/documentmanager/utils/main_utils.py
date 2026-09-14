"""
Punt d'entrada únic per guardar i llegir documents, independentment del servei
d'emmagatzematge. Mateix paper que `documentmanager/utils/main_utils.py` a
avsis-customers-backend, però aquí només hi ha implementat `hdd`.
"""

from django.conf import settings

from documentmanager.models import Document
from documentmanager.utils import hdd_service


class UnsupportedServiceError(Exception):
    pass


def _check_service(service):
    if service != Document.SERVICE_HDD:
        raise UnsupportedServiceError(f"Servei d'emmagatzematge no suportat: {service}")


def upload_document(
    file_obj,
    entity,
    entity_id=None,
    entity_token="",
    folder="",
    document_name=None,
    service=Document.SERVICE_HDD,
    uploaded_by=None,
    content_type=None,
    version=1,
    parent_document=None,
):
    _check_service(service)

    filename = document_name or getattr(file_obj, "name", "document.pdf")
    location = hdd_service.save_file(file_obj, folder or entity.lower(), filename)

    size = getattr(file_obj, "size", None)
    if size is None:
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)

    return Document.objects.create(
        entity=entity,
        entity_id=entity_id,
        entity_token=entity_token or "",
        folder=folder or entity.lower(),
        document_name=filename,
        location=location,
        content_type=content_type or getattr(file_obj, "content_type", "application/pdf"),
        size=size,
        service=service,
        uploaded_by=uploaded_by,
        version=version,
        parent_document=parent_document,
    )


def download_document(document):
    """Retorna els bytes del document, o None si no es pot llegir."""
    if not document or not document.location:
        return None
    _check_service(document.service)
    try:
        return hdd_service.read_file(document.location)
    except OSError:
        return None


def delete_document(document):
    """Baixa lògica del document i esborrat físic del fitxer."""
    if not document:
        return False
    _check_service(document.service)
    hdd_service.delete_file(document.location)
    document.is_active = False
    document.save(update_fields=["is_active", "updated_at"])
    return True


def get_default_service():
    return getattr(settings, "DOCUMENT_DEFAULT_SERVICE", Document.SERVICE_HDD)
