from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.models import User


class IsCeoOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.CEO
        )
