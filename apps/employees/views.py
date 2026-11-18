import csv
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from apps.core.mixins import RoleRequiredMixin
from apps.organizations.models import Department
from .models import Employee, EmployeeStatus, EmploymentType

class EmployeeListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Employee
    template_name = 'employees/list.html'
    context_object_name = 'employees'
    paginate_by = 15
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get_queryset(self):
        qs = Employee.objects.select_related('department', 'position', 'user').all()
        query = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('department', '').strip()
        status = self.request.GET.get('status', '').strip()

        if query:
            qs = qs.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(employee_id_number__icontains=query) |
                Q(user__email__icontains=query) |
                Q(position__title__icontains=query)
            )

        if dept_id:
            qs = qs.filter(department_id=dept_id)

        if status:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        context['statuses'] = EmployeeStatus.choices
        context['current_query'] = self.request.GET.get('q', '')
        context['current_department'] = self.request.GET.get('department', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['total_count'] = Employee.objects.count()
        return context

class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/detail.html'
    context_object_name = 'employee'

    def get_object(self, queryset=None):
        # Employees can view their own profile, HR can view anyone's
        pk = self.kwargs.get('pk')
        if pk:
            obj = get_object_or_404(Employee.objects.select_related('department', 'position', 'user'), pk=pk)
            user = self.request.user
            if user.role == 'EMPLOYEE' and not user.is_superuser:
                if not hasattr(user, 'employee_profile') or user.employee_profile.id != obj.id:
                    # Restrict access
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied("You can only view your own employee profile.")
            return obj
        return self.request.user.employee_profile

class EmployeeExportCSVView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="hrequest_employees.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID#', 'Full Name', 'Work Email', 'Department', 'Position', 'Type', 'Status', 'Location', 'Hire Date', 'Phone'])

        employees = Employee.objects.select_related('department', 'position', 'user').all()
        for emp in employees:
            writer.writerow([
                emp.employee_id_number,
                emp.full_name,
                emp.user.email,
                emp.department.name,
                emp.position.title,
                emp.get_employment_type_display(),
                emp.get_status_display(),
                emp.work_location,
                emp.hire_date.strftime('%Y-%m-%d'),
                emp.phone_number,
            ])
        return response
