import uuid

from django.contrib.auth.models import User
from django.db import models


def generate_token():
    return uuid.uuid4().hex


class Document(models.Model):
    """
    Un fitxer emmagatzemat. Manté la mateixa forma que el `Document` d'avsis
    (entitat + servei d'emmagatzematge + versions) però aquí només s'implementa
    el servei `hdd`; la resta queden reservats per no haver de migrar el model
    si algun dia s'hi afegeixen.

    Els fitxers no es modifiquen mai: cada signatura genera una fila nova amb
    `version` incrementada i `parent_document` apuntant a la versió anterior, de
    manera que l'original tal com ens l'han passat sempre es conserva intacte.
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


class DocumentSign(models.Model):
    """
    Sol·licitud de signatura: un conjunt de documents i un o més signants que
    els han de firmar **en cadena**, per ordre.

    El proveïdor (sign.aqua360) només accepta un destinatari per sessió, així
    que cada signant té la seva pròpia sessió: en tancar-se la d'un signant,
    s'obre la del següent amb el PDF que acaba de tornar firmat. L'estat
    d'aquest model és el de la sol·licitud sencera; el de cada signant viu a
    `DocumentSignSigner`.
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

    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_report = models.CharField(max_length=255, null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="document_signs"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document Sign"
        verbose_name_plural = "Document Signs"

    def __str__(self):
        return self.title or self.token

    def next_pending_signer(self):
        """El primer signant de la cadena que encara no ha firmat."""
        return self.signers.exclude(status=DocumentSignSigner.STATUS_SIGNED).first()

    def all_signed(self):
        return self.signers.exists() and not self.signers.exclude(
            status=DocumentSignSigner.STATUS_SIGNED
        ).exists()


class DocumentSignDocument(models.Model):
    """
    Un document dins d'una sol·licitud.

    `original_document` és el fitxer tal com ens l'han passat i no canvia mai.
    `current_document` és l'última versió de la cadena: l'original mentre ningú
    no hagi firmat, i després el PDF que ha tornat l'últim signant, que és el
    que s'envia al signant següent.
    """

    document_sign = models.ForeignKey(
        DocumentSign, on_delete=models.CASCADE, related_name="documents"
    )
    order = models.IntegerField(default=0)

    original_document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="sign_documents_as_original"
    )
    current_document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="sign_documents_as_current"
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.original_document.document_name or f"Document {self.id}"

    @property
    def is_signed(self):
        return self.current_document_id != self.original_document_id


class DocumentSignSigner(models.Model):
    """
    Un signant de la cadena. `order` marca el torn: el signant 2 no rep res fins
    que el signant 1 ha firmat.
    """

    STATUS_PENDING = 1
    STATUS_SENDED = 2
    STATUS_SIGNED = 3
    STATUS_EXPIRED = 4
    STATUS_ERROR = -1

    STATUS_CHOICES = DocumentSign.STATUS_CHOICES

    document_sign = models.ForeignKey(
        DocumentSign, on_delete=models.CASCADE, related_name="signers"
    )
    order = models.IntegerField(default=1)
    token = models.CharField(max_length=255, unique=True, default=generate_token)

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)

    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING)
    signed_at = models.DateTimeField(null=True, blank=True)
    error_report = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.order}. {self.name} <{self.email}>"


class DocumentSignSignature(models.Model):
    """
    Rastre d'una signatura concreta: quin signant ha produït quina versió de
    quin document. És el que permet reconstruir la cadena sencera d'un document
    (original → firmat pel signant 1 → firmat pel signant 2 → ...).
    """

    signer = models.ForeignKey(
        DocumentSignSigner, on_delete=models.CASCADE, related_name="signatures"
    )
    sign_document = models.ForeignKey(
        DocumentSignDocument, on_delete=models.CASCADE, related_name="signatures"
    )
    document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="sign_signatures"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["signer__order", "id"]
        unique_together = ("signer", "sign_document")

    def __str__(self):
        return f"{self.sign_document} firmat per {self.signer.name}"
