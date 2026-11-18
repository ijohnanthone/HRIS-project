from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

class RoleRequiredMixin(AccessMixin):
    """
    Verify that the current user is authenticated and has one of the specified roles.
    Superusers bypass role restrictions.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_role = getattr(request.user, 'role', None)
        if user_role not in self.allowed_roles:
            messages.error(request, "You do not have permission to access this resource.")
            raise PermissionDenied("Access restricted by role permissions.")

        return super().dispatch(request, *args, **kwargs)
