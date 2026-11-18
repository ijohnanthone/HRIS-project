from django.urls import path
from .views_admin import (
    SystemAdminPortalView,
    AdminUserCreateView,
    AdminUserUpdateRoleView,
    AdminUserToggleStatusView,
    AdminUserResetPasswordView,
)

app_name = 'system_admin'

urlpatterns = [
    path('', SystemAdminPortalView.as_view(), name='portal'),
    path('users/create/', AdminUserCreateView.as_view(), name='user_create'),
    path('users/<uuid:pk>/role/', AdminUserUpdateRoleView.as_view(), name='user_update_role'),
    path('users/<uuid:pk>/toggle-status/', AdminUserToggleStatusView.as_view(), name='user_toggle_status'),
    path('users/<uuid:pk>/reset-password/', AdminUserResetPasswordView.as_view(), name='user_reset_password'),
]
