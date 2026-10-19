from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """
    Allows access only to authenticated superusers.
    """
    message = "You must be a superuser to access this endpoint."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
