import django_filters
from django.db.models import Q

from .models import Document, DocumentSign


class DocumentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="document_name", lookup_expr="icontains")

    class Meta:
        model = Document
        fields = ["entity", "entity_id", "entity_token", "is_active", "service"]


class DocumentSignFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    # `status` admet una llista separada per comes ("1,2") per encaixar amb els
    # filtres multiselecció del frontal.
    status = django_filters.CharFilter(method="filter_status")

    class Meta:
        model = DocumentSign
        fields = ["otp_email"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(otp_name__icontains=value)
            | Q(otp_email__icontains=value)
            | Q(token__icontains=value)
        )

    def filter_status(self, queryset, name, value):
        if not value:
            return queryset
        values = [
            int(item) for item in str(value).split(",") if item.strip().lstrip("-").isdigit()
        ]
        return queryset.filter(status__in=values) if values else queryset
