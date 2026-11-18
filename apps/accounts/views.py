from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .forms import EmailAuthenticationForm
from .models import CustomUser, UserRole

class HRequestLoginView(FormView):
    template_name = 'accounts/login.html'
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)
        messages.success(self.request, f"Welcome back, {user.display_name}!")
        return super().form_valid(form)

class HRequestLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been successfully logged out.")
        return redirect('accounts:login')

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Unified dashboard router: dynamically serves role-tailored dashboard template
    based on the authenticated user's role.
    """
    def get_template_names(self):
        user = self.request.user
        if user.is_superuser or user.role == UserRole.SUPER_ADMIN:
            return ['dashboard/super_admin.html']
        elif user.role == UserRole.HR_ADMIN:
            return ['dashboard/hr_admin.html']
        elif user.role == UserRole.HR_STAFF:
            return ['dashboard/hr_staff.html']
        else:
            return ['dashboard/employee.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['role'] = user.role
        context['role_display'] = user.get_role_display()
        today = timezone.now().date()
        context['today'] = today

        # Import domain models
        from apps.employees.models import Employee, EmployeeStatus
        from apps.organizations.models import Department
        from apps.attendance.models import Attendance, AttendanceStatus
        from apps.requests.models import DocumentRequest, RequestStatus
        from apps.payslips.models import PayslipRecord
        from apps.announcements.models import Announcement
        from apps.core.models import AuditLog

        # Universal widgets: announcements
        announcements_qs = Announcement.objects.filter(is_published=True).select_related('author', 'target_department')
        if user.role == UserRole.EMPLOYEE and hasattr(user, 'employee_profile'):
            dept = user.employee_profile.department
            announcements_qs = announcements_qs.filter(Q(target_department__isnull=True) | Q(target_department=dept))
        context['recent_announcements'] = announcements_qs[:4]

        # Role-specific analytics
        if user.is_superuser or user.role == UserRole.SUPER_ADMIN:
            context['total_users'] = CustomUser.objects.count()
            context['users_by_role'] = {
                'super_admin': CustomUser.objects.filter(role=UserRole.SUPER_ADMIN).count(),
                'hr_admin': CustomUser.objects.filter(role=UserRole.HR_ADMIN).count(),
                'hr_staff': CustomUser.objects.filter(role=UserRole.HR_STAFF).count(),
                'employee': CustomUser.objects.filter(role=UserRole.EMPLOYEE).count(),
            }
            context['total_employees'] = Employee.objects.count()
            context['total_departments'] = Department.objects.count()
            context['audit_logs'] = AuditLog.objects.select_related('actor').order_by('-timestamp')[:10]

        elif user.role == UserRole.HR_ADMIN:
            context['total_employees'] = Employee.objects.filter(status=EmployeeStatus.ACTIVE).count()
            context['total_departments'] = Department.objects.count()
            context['today_present'] = Attendance.objects.filter(date=today, clock_in__isnull=False).count()
            context['pending_coe_count'] = DocumentRequest.objects.filter(status=RequestStatus.PENDING).count()
            context['recent_requests'] = DocumentRequest.objects.select_related('employee', 'employee__department').order_by('-created_at')[:5]
            context['recent_employees'] = Employee.objects.select_related('department', 'position', 'user').order_by('-created_at')[:5]

        elif user.role == UserRole.HR_STAFF:
            context['today_attendances'] = Attendance.objects.filter(date=today).select_related('employee', 'employee__department').order_by('-clock_in')[:8]
            context['today_present_count'] = Attendance.objects.filter(date=today, clock_in__isnull=False).count()
            context['today_late_count'] = Attendance.objects.filter(date=today, status=AttendanceStatus.LATE).count()
            context['pending_requests'] = DocumentRequest.objects.filter(status=RequestStatus.PENDING).select_related('employee')[:5]
            context['total_employees'] = Employee.objects.count()

        elif user.role == UserRole.EMPLOYEE:
            if hasattr(user, 'employee_profile'):
                emp = user.employee_profile
                context['employee'] = emp
                context['my_today_attendance'] = Attendance.objects.filter(employee=emp, date=today).first()
                context['my_recent_attendance'] = Attendance.objects.filter(employee=emp).order_by('-date')[:5]
                context['my_requests'] = DocumentRequest.objects.filter(employee=emp).order_by('-created_at')[:5]
                context['latest_payslip'] = PayslipRecord.objects.filter(employee=emp).select_related('payroll_period').order_by('-payroll_period__period_year', '-payroll_period__period_month').first()
            else:
                context['employee'] = None
                context['my_today_attendance'] = None
                context['my_recent_attendance'] = []
                context['my_requests'] = []
                context['latest_payslip'] = None

        return context

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context
