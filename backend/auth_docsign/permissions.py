class PermissionManager:
    """
    Utilitats sobre els permisos de Django, amb la mateixa forma que a
    `avsis-customers-backend` perquè el frontal pugui reaprofitar el mateix
    contracte (`/auth/permission/my-permissions/`).
    """

    @staticmethod
    def has_permission(user, codename):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.user_permissions.filter(codename=codename).exists() or any(
            group.permissions.filter(codename=codename).exists() for group in user.groups.all()
        )

    @staticmethod
    def get_model_permissions(user, app_label, model):
        if not user or not user.is_authenticated:
            return {"can_view": False, "can_add": False, "can_change": False, "can_delete": False}
        prefix = f"{app_label}."
        return {
            "can_view": user.has_perm(f"{prefix}view_{model}"),
            "can_add": user.has_perm(f"{prefix}add_{model}"),
            "can_change": user.has_perm(f"{prefix}change_{model}"),
            "can_delete": user.has_perm(f"{prefix}delete_{model}"),
        }

    @staticmethod
    def get_all_permissions(user):
        if not user or not user.is_authenticated:
            return []
        if user.is_superuser:
            from django.contrib.auth.models import Permission

            return list(
                Permission.objects.values_list("content_type__app_label", "codename")
            )
        return sorted(user.get_all_permissions())
