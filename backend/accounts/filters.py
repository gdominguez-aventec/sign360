import django_filters
from django.contrib.auth.models import Group, User


class UserFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = User
        fields = ["is_active", "is_staff"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(username__icontains=value) | queryset.filter(
            email__icontains=value
        )


class GroupFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Group
        fields = []
