import sys
import platform
import django
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from apps.core.mixins import RoleRequiredMixin
from apps.accounts.models import CustomUser, UserRole
from apps.core.models import AuditLog
from .forms_admin import AdminUserCreationForm, AdminUserRoleForm, AdminResetPasswordForm

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

class SystemAdminPortalView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    Dedicated SaaS-native System Administration Console.
    Replaces raw/unstyled backend django admin with a sleek, user-friendly UI.
    """
    template_name = 'admin/system_admin_portal.html'
    allowed_roles = ['SUPER_ADMIN']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        role_filter = self.request.GET.get('role', '').strip()

        users_qs = CustomUser.objects.select_related('employee_profile').order_by('-date_joined')
        if q:
            users_qs = users_qs.filter(
                Q(email__icontains=q) |
                Q(employee_profile__first_name__icontains=q) |
                Q(employee_profile__last_name__icontains=q) |
                Q(employee_profile__employee_id_number__icontains=q)
            )
        if role_filter:
            users_qs = users_qs.filter(role=role_filter)

        context['users'] = users_qs
        context['current_q'] = q
        context['current_role'] = role_filter
        context['roles'] = UserRole.choices
        context['total_users_count'] = CustomUser.objects.count()
        context['active_users_count'] = CustomUser.objects.filter(is_active=True).count()
        context['create_form'] = AdminUserCreationForm()
        context['reset_pwd_form'] = AdminResetPasswordForm()

        # Telemetry & System Diagnostics
        from django.db import connection
        context['system_telemetry'] = {
            'django_version': django.get_version(),
            'python_version': platform.python_version(),
            'os_platform': f"{platform.system()} {platform.release()}",
            'db_engine': connection.vendor.upper(),
            'db_name': connection.settings_dict.get('NAME', 'HRequest Primary'),
            'debug_mode': django.conf.settings.DEBUG,
        }

        # Role breakdown counts
        context['role_counts'] = {
            'super_admin': CustomUser.objects.filter(role=UserRole.SUPER_ADMIN).count(),
            'hr_admin': CustomUser.objects.filter(role=UserRole.HR_ADMIN).count(),
            'hr_staff': CustomUser.objects.filter(role=UserRole.HR_STAFF).count(),
            'employee': CustomUser.objects.filter(role=UserRole.EMPLOYEE).count(),
        }

        # Recent audit logs
        context['recent_audits'] = AuditLog.objects.select_related('actor').order_by('-timestamp')[:12]
        return context

class AdminUserCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN']

    def post(self, request, *args, **kwargs):
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            AuditLog.objects.create(
                actor=request.user,
                action='CREATE_USER',
                model_name='CustomUser',
                object_id=str(user.id),
                changes={'email': user.email, 'role': user.role},
                ip_address=get_client_ip(request)
            )
            messages.success(request, f"User account '{user.email}' created successfully as {user.get_role_display()}!")
        else:
            for field, errs in form.errors.items():
                messages.error(request, f"{field.capitalize()}: {errs.as_text()}")
        return redirect('system_admin:portal')

class AdminUserUpdateRoleView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN']

    def post(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(CustomUser, pk=pk)
        new_role = request.POST.get('role')
        if new_role in UserRole.values:
            old_role = target_user.role
            target_user.role = new_role
            if new_role == UserRole.SUPER_ADMIN:
                target_user.is_staff = True
                target_user.is_superuser = True
            elif new_role in [UserRole.HR_ADMIN, UserRole.HR_STAFF]:
                target_user.is_staff = True
                target_user.is_superuser = False
            else:
                target_user.is_staff = False
                target_user.is_superuser = False

            target_user.save()
            AuditLog.objects.create(
                actor=request.user,
                action='UPDATE_ROLE',
                model_name='CustomUser',
                object_id=str(target_user.id),
                changes={'old_role': old_role, 'new_role': new_role},
                ip_address=get_client_ip(request)
            )
            messages.success(request, f"Role for {target_user.email} updated to {target_user.get_role_display()}.")
        return redirect('system_admin:portal')

class AdminUserToggleStatusView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN']

    def post(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(CustomUser, pk=pk)
        if target_user == request.user:
            messages.error(request, "You cannot deactivate your own active session account.")
            return redirect('system_admin:portal')

        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=['is_active'])
        status_label = "Activated" if target_user.is_active else "Deactivated"
        AuditLog.objects.create(
            actor=request.user,
            action='TOGGLE_STATUS',
            model_name='CustomUser',
            object_id=str(target_user.id),
            changes={'is_active': target_user.is_active},
            ip_address=get_client_ip(request)
        )
        messages.success(request, f"User {target_user.email} has been {status_label}.")
        return redirect('system_admin:portal')

class AdminUserResetPasswordView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN']

    def post(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(CustomUser, pk=pk)
        new_pwd = request.POST.get('new_password', '').strip()
        if len(new_pwd) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('system_admin:portal')

        target_user.set_password(new_pwd)
        target_user.save(update_fields=['password'])
        AuditLog.objects.create(
            actor=request.user,
            action='RESET_PASSWORD',
            model_name='CustomUser',
            object_id=str(target_user.id),
            changes={'event': 'Password manually reset by Super Admin'},
            ip_address=get_client_ip(request)
        )
        messages.success(request, f"Password for {target_user.email} successfully updated.")
        return redirect('system_admin:portal')
