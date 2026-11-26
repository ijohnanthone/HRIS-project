import csv
import datetime
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from apps.core.mixins import RoleRequiredMixin
from apps.organizations.models import Department, Position
from apps.accounts.models import CustomUser, UserRole
from apps.documents.forms import EmployeeDocumentUploadForm
from .models import Employee, EmployeeStatus, EmploymentType, WorkLocation
from .forms import (
    OnboardingStep1Form,
    OnboardingStep2Form,
    OnboardingStep3Form,
    OnboardingStep4Form,
    EmployeeEditForm,
)

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
        pk = self.kwargs.get('pk')
        if pk:
            obj = get_object_or_404(Employee.objects.select_related('department', 'position', 'user'), pk=pk)
            user = self.request.user
            if user.role == 'EMPLOYEE' and not user.is_superuser:
                if not hasattr(user, 'employee_profile') or user.employee_profile.id != obj.id:
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied("You can only view your own employee profile.")
            return obj
        return self.request.user.employee_profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        emp = self.object

        # Retrieve documents based on permission level
        docs = emp.documents.select_related('uploaded_by').all()
        if user.role == 'EMPLOYEE' or user.role == 'HR_STAFF':
            docs = docs.filter(is_confidential=False)

        context['documents'] = docs
        context['document_form'] = EmployeeDocumentUploadForm()
        context['can_upload_doc'] = user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']
        return context

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

class EmployeeOnboardingWizardView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Multi-Step Onboarding Wizard matching UI Reference Screen 4:
    Part 1 -> Part 2 -> Part 3 -> Part 4 -> Finish
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']
    template_name = 'employees/onboarding_wizard.html'

    def get_session_data(self):
        return self.request.session.get('onboarding_data', {})

    def save_session_data(self, data):
        session_data = self.get_session_data()
        session_data.update(data)
        self.request.session['onboarding_data'] = session_data

    def get(self, request, step=1):
        step = int(step)
        if step < 1 or step > 5:
            return redirect('employees:onboard_step', step=1)

        data = self.get_session_data()
        form = None

        if step == 1:
            form = OnboardingStep1Form(initial=data)
        elif step == 2:
            form = OnboardingStep2Form(initial=data)
        elif step == 3:
            form = OnboardingStep3Form(initial=data)
        elif step == 4:
            form = OnboardingStep4Form(initial=data)
        elif step == 5:
            # Review / Finish step
            context = self.get_finish_context(data)
            context['current_step'] = 5
            return render(request, self.template_name, context)

        return render(request, self.template_name, {
            'form': form,
            'current_step': step,
            'session_data': data,
            'candidate_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or "New Employee"
        })

    def post(self, request, step=1):
        step = int(step)
        data = self.get_session_data()

        if step == 1:
            form = OnboardingStep1Form(request.POST)
            if form.is_valid():
                cleaned = form.cleaned_data
                if cleaned.get('birth_date'):
                    cleaned['birth_date'] = cleaned['birth_date'].strftime('%Y-%m-%d')
                self.save_session_data(cleaned)
                return redirect('employees:onboard_step', step=2)

        elif step == 2:
            form = OnboardingStep2Form(request.POST)
            if form.is_valid():
                cleaned = form.cleaned_data
                self.save_session_data({
                    'department_id': cleaned['department'].id,
                    'department_name': cleaned['department'].name,
                    'position_id': cleaned['position'].id,
                    'position_title': cleaned['position'].title,
                    'employment_type': cleaned['employment_type'],
                    'hire_date': cleaned['hire_date'].strftime('%Y-%m-%d'),
                    'probation_end_date': cleaned['probation_end_date'].strftime('%Y-%m-%d') if cleaned.get('probation_end_date') else None,
                })
                return redirect('employees:onboard_step', step=3)

        elif step == 3:
            form = OnboardingStep3Form(request.POST)
            if form.is_valid():
                cleaned = form.cleaned_data
                self.save_session_data({
                    'work_email': cleaned['work_email'],
                    'password': cleaned['password'],
                    'role': cleaned['role'],
                })
                return redirect('employees:onboard_step', step=4)

        elif step == 4:
            form = OnboardingStep4Form(request.POST)
            if form.is_valid():
                cleaned = form.cleaned_data
                self.save_session_data(cleaned)
                return redirect('employees:onboard_step', step=5)

        elif step == 5:
            # Commit atomic creation
            return self.complete_onboarding(request)

        return render(request, self.template_name, {
            'form': form,
            'current_step': step,
            'session_data': data,
            'candidate_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or "New Employee"
        })

    def get_finish_context(self, data):
        dept_name = data.get('department_name', 'Not Specified')
        pos_title = data.get('position_title', 'Not Specified')
        loc_val = data.get('work_location', '')
        loc_display = dict(WorkLocation.choices).get(loc_val, loc_val)
        return {
            'summary': data,
            'candidate_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'dept_name': dept_name,
            'pos_title': pos_title,
            'hire_date': data.get('hire_date'),
            'work_location': loc_display,
            'classification': data.get('employment_type'),
            'work_email': data.get('work_email'),
            'employee_id': data.get('employee_id_number'),
        }

    def complete_onboarding(self, request):
        data = self.get_session_data()
        try:
            with transaction.atomic():
                # 1. Create CustomUser
                user = CustomUser.objects.create_user(
                    email=data['work_email'],
                    password=data['password'],
                    role=data.get('role', UserRole.EMPLOYEE),
                    is_active=True
                )

                # 2. Parse dates
                hire_date = datetime.datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
                birth_date = None
                if data.get('birth_date'):
                    birth_date = datetime.datetime.strptime(data['birth_date'], '%Y-%m-%d').date()

                probation_end_date = None
                if data.get('probation_end_date'):
                    probation_end_date = datetime.datetime.strptime(data['probation_end_date'], '%Y-%m-%d').date()

                # 3. Create Employee
                emp = Employee.objects.create(
                    user=user,
                    employee_id_number=data['employee_id_number'],
                    first_name=data['first_name'],
                    middle_name=data.get('middle_name', ''),
                    last_name=data['last_name'],
                    department_id=data['department_id'],
                    position_id=data['position_id'],
                    employment_type=data['employment_type'],
                    status=EmployeeStatus.ACTIVE,
                    work_location=data.get('work_location', 'Main Office'),
                    hire_date=hire_date,
                    probation_end_date=probation_end_date,
                    birth_date=birth_date,
                    phone_number=data.get('phone_number', ''),
                    emergency_contact_name=data.get('emergency_contact_name', ''),
                    emergency_contact_phone=data.get('emergency_contact_phone', ''),
                )

                # Clear session
                if 'onboarding_data' in request.session:
                    del request.session['onboarding_data']

                messages.success(request, f"Employee {emp.full_name} ({emp.employee_id_number}) has been successfully onboarded!")
                return redirect('employees:detail', pk=emp.id)

        except Exception as e:
            messages.error(request, f"Error completing onboarding: {str(e)}")
            return redirect('employees:onboard_step', step=5)


class EmployeeTerminateView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Allows HR Admin / Super Admin to terminate (fire) an employee:
    sets status to TERMINATED and deactivates their login account while preserving audit history.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def post(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(Employee.objects.select_related('user'), pk=pk)
        if emp.user_id == request.user.id:
            messages.error(request, "You cannot terminate your own active account.")
            return redirect('employees:detail', pk=emp.id)

        from apps.core.models import AuditLog
        with transaction.atomic():
            emp.status = EmployeeStatus.TERMINATED
            emp.save(update_fields=['status'])
            emp.user.is_active = False
            emp.user.save(update_fields=['is_active'])

            AuditLog.objects.create(
                actor=request.user,
                action='EMPLOYEE_TERMINATED',
                model_name='Employee',
                object_id=str(emp.id),
                changes={'details': f"Terminated employee {emp.full_name} (ID: {emp.employee_id_number}) and deactivated login account."}
            )

        messages.warning(request, f"Employee {emp.full_name} ({emp.employee_id_number}) has been terminated and their login access disabled.")
        next_url = request.POST.get('next')
        return redirect(next_url or 'employees:list')


class EmployeeDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Allows HR Admin / Super Admin to permanently delete an employee and their login account.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def post(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(Employee.objects.select_related('user'), pk=pk)
        if emp.user_id == request.user.id:
            messages.error(request, "You cannot delete your own active account.")
            return redirect('employees:detail', pk=emp.id)

        from apps.core.models import AuditLog
        emp_name = emp.full_name
        emp_id_num = emp.employee_id_number
        emp_uuid = str(emp.id)
        user_obj = emp.user

        with transaction.atomic():
            AuditLog.objects.create(
                actor=request.user,
                action='EMPLOYEE_DELETED',
                model_name='Employee',
                object_id=emp_uuid,
                changes={'details': f"Permanently deleted employee {emp_name} (ID: {emp_id_num}) and associated user account."}
            )
            user_obj.delete()

        messages.success(request, f"Employee {emp_name} ({emp_id_num}) has been permanently deleted from the system.")
        return redirect('employees:list')


class EmployeeUpdateView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Allows HR Admin, HR Staff, and Super Admin to edit an employee's profile
    (e.g., fix name typos, update work location/site, department, position, or contact details).
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']
    template_name = 'employees/edit.html'

    def get(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(Employee.objects.select_related('user', 'department', 'position'), pk=pk)
        form = EmployeeEditForm(instance=emp)
        return render(request, self.template_name, {'form': form, 'employee': emp})

    def post(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(Employee.objects.select_related('user', 'department', 'position'), pk=pk)
        form = EmployeeEditForm(request.POST, instance=emp)
        if form.is_valid():
            from apps.core.models import AuditLog
            with transaction.atomic():
                updated_emp = form.save()
                new_email = form.cleaned_data['work_email']
                if updated_emp.user.email != new_email:
                    updated_emp.user.email = new_email
                    updated_emp.user.save(update_fields=['email'])

                # Sync active user status if HR changed employment status to/from TERMINATED
                should_be_active = updated_emp.status != EmployeeStatus.TERMINATED
                if updated_emp.user.is_active != should_be_active:
                    updated_emp.user.is_active = should_be_active
                    updated_emp.user.save(update_fields=['is_active'])

                AuditLog.objects.create(
                    actor=request.user,
                    action='EMPLOYEE_UPDATED',
                    model_name='Employee',
                    object_id=str(updated_emp.id),
                    changes={'details': f"Updated profile for {updated_emp.full_name} (ID: {updated_emp.employee_id_number})."}
                )

            messages.success(request, f"Profile for {updated_emp.full_name} has been updated.")
            return redirect('employees:detail', pk=updated_emp.id)

        return render(request, self.template_name, {'form': form, 'employee': emp})
