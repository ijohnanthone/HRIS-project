import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from apps.core.mixins import RoleRequiredMixin
from apps.employees.models import Employee
from apps.organizations.models import Department
from .models import PayslipRecord, PayrollPeriod, PayslipStatus
from .forms import PayslipUploadForm, PayrollPeriodForm

class MasterPayslipListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    Master payroll disbursement roster matching UI Reference Screen 5.
    Accessible to HR Admin and HR Staff.
    """
    model = PayslipRecord
    template_name = 'payslips/master_list.html'
    context_object_name = 'payslips'
    paginate_by = 25
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get_queryset(self):
        qs = PayslipRecord.objects.select_related(
            'employee__department',
            'employee__position',
            'payroll_period',
            'uploaded_by'
        )

        period_id = self.request.GET.get('period', '').strip()
        dept_id = self.request.GET.get('department', '').strip()
        status = self.request.GET.get('status', '').strip()
        query = self.request.GET.get('q', '').strip()

        if period_id:
            qs = qs.filter(payroll_period_id=period_id)
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)
        if status:
            qs = qs.filter(status=status)
        if query:
            qs = qs.filter(
                Q(employee__first_name__icontains=query) |
                Q(employee__last_name__icontains=query) |
                Q(employee__employee_id_number__icontains=query)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periods'] = PayrollPeriod.objects.all()
        context['departments'] = Department.objects.all()
        context['statuses'] = PayslipStatus.choices
        context['upload_form'] = PayslipUploadForm()
        context['current_period'] = self.request.GET.get('period', '')
        context['current_dept'] = self.request.GET.get('department', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_q'] = self.request.GET.get('q', '')

        # Total disbursed calculation for filtered queryset
        total_sum = self.get_queryset().aggregate(Sum('total_salary'))['total_salary__sum'] or 0
        context['total_disbursed_sum'] = total_sum
        return context

class PayslipUploadView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Uploads an employee payslip PDF file and attaches it to a payroll period.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def post(self, request, *args, **kwargs):
        form = PayslipUploadForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                emp = form.cleaned_data['employee']
                period = form.cleaned_data['payroll_period']
                is_replacement = form.cleaned_data.get('is_replacement')

                if is_replacement:
                    # Remove superseded duplicate record if replacing
                    PayslipRecord.objects.filter(employee=emp, payroll_period=period).delete()

                payslip = form.save(commit=False)
                payslip.uploaded_by = request.user
                payslip.is_released = True
                payslip.save()

            messages.success(request, f"Payslip for {payslip.employee.full_name} ({payslip.payroll_period.label}) uploaded successfully.")
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())

        return redirect('payslips:master_list')

class MyPayslipsView(LoginRequiredMixin, ListView):
    """
    Employee portal: View and download personal released payslips.
    """
    model = PayslipRecord
    template_name = 'payslips/my_payslips.html'
    context_object_name = 'my_payslips'
    paginate_by = 24

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'employee_profile'):
            return PayslipRecord.objects.none()

        return PayslipRecord.objects.filter(
            employee=user.employee_profile,
            is_released=True
        ).select_related('payroll_period')

class SecurePayslipDownloadView(LoginRequiredMixin, View):
    """
    Guarded download controller for confidential employee payslips.
    Restricts access strictly to HR Admins, Super Admins, and the owner employee.
    """
    def get(self, request, pk, *args, **kwargs):
        payslip = get_object_or_404(PayslipRecord.objects.select_related('employee__user'), pk=pk)
        user = request.user

        # 1. Authorization Guard
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']:
            pass
        elif user.role == 'EMPLOYEE':
            if payslip.employee.user_id != user.id:
                raise PermissionDenied("You can only access and download your own personal payslips.")
            if not payslip.is_released:
                raise PermissionDenied("This payslip has not been released yet.")
        else:
            raise PermissionDenied("Unauthorized payslip access.")

        if not payslip.payslip_file or not payslip.payslip_file.storage.exists(payslip.payslip_file.name):
            raise Http404("Payslip PDF document not found in private vault.")

        content_type, _ = mimetypes.guess_type(payslip.payslip_file.name)
        response = FileResponse(payslip.payslip_file.open('rb'), content_type=content_type or 'application/pdf')
        filename = f"Payslip_{payslip.employee.employee_id_number}_{payslip.payroll_period.label.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
