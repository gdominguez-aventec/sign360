import uuid

from django.contrib.auth.models import User
from django.db import models


class Document(models.Model):
    """
    Un fitxer emmagatzemat. Manté la mateixa forma que el `Document` d'avsis
    (entitat + servei d'emmagatzematge + versions) però aquí només s'implementa
    el servei `hdd`; la resta queden reservats per no haver de migrar el model
    si algun dia s'hi afegeixen.
    """

    SERVICE_HDD = "hdd"
    SERVICE_CHOICES = [
        (SERVICE_HDD, "HDD"),
        ("azure", "Azure"),
        ("aws", "AWS"),
        ("ftp", "FTP"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date = models.DateField(null=True, blank=True)

    entity = models.CharField(max_length=255, null=True, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    entity_token = models.CharField(max_length=255, null=True, blank=True)

    folder = models.CharField(max_length=255, null=True, blank=True)
    document_name = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=500, null=True, blank=True)
    location_url = models.URLField(max_length=500, null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)
    size = models.BigIntegerField(null=True, blank=True)

    version = models.IntegerField(default=1)
    parent_document = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="versions"
    )

    service = models.CharField(max_length=50, choices=SERVICE_CHOICES, default=SERVICE_HDD)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.document_name or f"Document {self.id}"


def generate_token():
    return uuid.uuid4().hex


class DocumentSign(models.Model):
    """
    Sol·licitud de signatura d'un document. El cicle de vida el marca `status`:
    PENDING (creada) → SENDED (sessió creada al proveïdor i enviada al signant)
    → SIGNED / EXPIRED, o ERROR si el proveïdor ha fallat.
    """

    STATUS_PENDING = 1
    STATUS_SENDED = 2
    STATUS_SIGNED = 3
    STATUS_EXPIRED = 4
    STATUS_ERROR = -1

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENDED, "Sended"),
        (STATUS_SIGNED, "Signed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_ERROR, "Error"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=255, unique=True, default=generate_token)

    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    document_file = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_signs_as_file",
    )
    document_file_signed = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_signs_as_signed_file",
    )
    signed_at = models.DateTimeField(null=True, blank=True)

    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_report = models.CharField(max_length=255, null=True, blank=True)

    # Dades del signant (l'OTP l'envia el proveïdor per correu/SMS)
    otp_name = models.CharField(max_length=255, null=True, blank=True)
    otp_email = models.EmailField(null=True, blank=True)
    otp_phone = models.CharField(max_length=50, null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="document_signs"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document Sign"
        verbose_name_plural = "Document Signs"

    def __str__(self):
        return self.title or self.token
