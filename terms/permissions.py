from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSuperUserOrReadOnly(BasePermission):
    """
    Custom permission for Terms and Conditions:
    - Any user (anonymous visitors, regular authenticated customers, etc.) can show (read/view) it via GET, HEAD, OPTIONS.
    - Only authenticated super admin users (request.user.is_superuser == True) can edit (POST, PUT, PATCH, DELETE) it.
    """
    message = "Only a super admin can create, modify, or delete Terms and Conditions."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )
