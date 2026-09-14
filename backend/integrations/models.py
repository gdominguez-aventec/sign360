from django.db import models


class IntegrationRequestLog(models.Model):
    """Traça de cada crida amb el proveïdor extern, d'anada i de tornada."""

    DIRECTION_INBOUND = "inbound"
    DIRECTION_OUTBOUND = "outbound"

    DIRECTION_CHOICES = [
        (DIRECTION_INBOUND, "Inbound"),
        (DIRECTION_OUTBOUND, "Outbound"),
    ]

    provider = models.CharField(max_length=100)
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} {self.method} {self.endpoint} ({self.success})"


class SigningSession(models.Model):
    """
    Sessió de signatura oberta al proveïdor per a **un signant**.

    El proveïdor només accepta un destinatari per sessió, així que una
    sol·licitud amb tres signants genera tres sessions consecutives.
    """

    STATUS_PENDING = "pending"
    STATUS_SIGNED = "signed"
    STATUS_EXPIRED = "expired"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SIGNED, "Signed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_FAILED, "Failed"),
    ]

    signer = models.ForeignKey(
        "documentmanager.DocumentSignSigner",
        on_delete=models.CASCADE,
        related_name="signing_sessions",
    )
    session_id = models.CharField(max_length=64, unique=True)
    external_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    signing_url = models.URLField(max_length=500, blank=True)
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.EmailField()
    recipient_phone = models.CharField(max_length=50, blank=True)
    callback_url = models.URLField(max_length=500, blank=True)
    email_sent = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Correspondència entre els ids que el proveïdor assigna als documents de la
    # sessió i els nostres `DocumentSignDocument`: {"<provider_doc_id>": <id>}.
    # Sense això no sabríem a quin document nostre correspon cada PDF firmat que
    # ens torna el webhook quan la sessió en porta més d'un.
    document_map = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Signing {self.session_id} ({self.status})"
