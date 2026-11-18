import csv
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from apps.core.mixins import RoleRequiredMixin
from apps.employees.models import Employee, EmployeeStatus, EmploymentType
from apps.organizations.models import Department, Position
from apps.attendance.models import Attendance, AttendanceStatus
from apps.payslips.models import PayslipRecord, PayrollPeriod
from apps.requests.models import DocumentRequest, RequestStatus

class ReportsDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    Central Executive HR Analytics & Reporting Hub.
    Combines headcount demographics, punctuality, payroll disbursements,
    and COE turnaround metrics.
    """
    template_name = 'reports/dashboard.html'
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_employees = Employee.objects.count()
        context['total_employees'] = total_employees

        # 1. Department Breakdown & Headcount Share
        dept_data = []
        for dept in Department.objects.annotate(emp_count=Count('employees')).order_by('-emp_count'):
            pct = round((dept.emp_count / total_employees * 100), 1) if total_employees > 0 else 0
            dept_data.append({
                'id': dept.id,
                'name': dept.name,
                'code': dept.code,
                'count': dept.emp_count,
                'percentage': pct,
            })
        context['department_breakdown'] = dept_data

        # 2. Employment Type Breakdown
        type_data = []
        for type_val, type_lbl in EmploymentType.choices:
            count = Employee.objects.filter(employment_type=type_val).count()
            pct = round((count / total_employees * 100), 1) if total_employees > 0 else 0
            type_data.append({
                'label': type_lbl,
                'count': count,
                'percentage': pct
            })
        context['employment_types'] = type_data

        # 3. Work Location Distribution
        context['locations'] = Employee.objects.values('work_location').annotate(total=Count('id')).order_by('-total')

        # 4. Attendance & Punctuality Analytics
        total_attendance = Attendance.objects.count()
        present_count = Attendance.objects.filter(status=AttendanceStatus.PRESENT).count()
        late_count = Attendance.objects.filter(status=AttendanceStatus.LATE).count()
        half_day_count = Attendance.objects.filter(status=AttendanceStatus.HALF_DAY).count()
        absent_count = Attendance.objects.filter(status=AttendanceStatus.ABSENT).count()

        punctuality_rate = round((present_count / total_attendance * 100), 1) if total_attendance > 0 else 100.0

        context['attendance_metrics'] = {
            'total_logs': total_attendance,
            'present_count': present_count,
            'late_count': late_count,
            'half_day_count': half_day_count,
            'absent_count': absent_count,
            'punctuality_rate': punctuality_rate,
        }

        # 5. Payroll Summary (in PHP)
        latest_period = PayrollPeriod.objects.order_by('-period_year', '-period_month').first()
        context['latest_period'] = latest_period
        if latest_period:
            period_payslips = PayslipRecord.objects.filter(payroll_period=latest_period)
            total_disbursed = period_payslips.aggregate(Sum('total_salary'))['total_salary__sum'] or 0
            avg_salary = period_payslips.aggregate(Avg('total_salary'))['total_salary__avg'] or 0
            context['payroll_metrics'] = {
                'total_disbursed': total_disbursed,
                'avg_salary': avg_salary,
                'record_count': period_payslips.count(),
            }
        else:
            context['payroll_metrics'] = {
                'total_disbursed': 0,
                'avg_salary': 0,
                'record_count': 0,
            }

        # 6. Document & COE Request Telemetry
        total_coe = DocumentRequest.objects.count()
        approved_coe = DocumentRequest.objects.filter(status=RequestStatus.APPROVED).count()
        pending_coe = DocumentRequest.objects.filter(status=RequestStatus.PENDING).count()
        rejected_coe = DocumentRequest.objects.filter(status=RequestStatus.REJECTED).count()

        approval_rate = round((approved_coe / total_coe * 100), 1) if total_coe > 0 else 0
        context['coe_metrics'] = {
            'total_requests': total_coe,
            'approved_count': approved_coe,
            'pending_count': pending_coe,
            'rejected_count': rejected_coe,
            'approval_rate': approval_rate,
        }

        return context

class ExportWorkforceCSVView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        filename = f"HRequest_Workforce_Report_{timezone.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Employee ID', 'Full Name', 'Department', 'Position', 'Employment Type', 'Status', 'Work Location', 'Hire Date', 'Email'])

        for emp in Employee.objects.select_related('department', 'position', 'user').order_by('employee_id_number'):
            writer.writerow([
                emp.employee_id_number,
                emp.full_name,
                emp.department.name if emp.department else '',
                emp.position.title if emp.position else '',
                emp.get_employment_type_display(),
                emp.get_status_display(),
                emp.work_location,
                emp.hire_date.strftime('%Y-%m-%d') if emp.hire_date else '',
                emp.user.email if emp.user else '',
            ])
        return response

class ExportAttendanceCSVView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        filename = f"HRequest_Attendance_Report_{timezone.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Employee ID', 'Employee Name', 'Department', 'Clock In', 'Clock Out', 'Status', 'Source', 'IP Address'])

        for att in Attendance.objects.select_related('employee__department').order_by('-date', '-clock_in'):
            writer.writerow([
                att.date.strftime('%Y-%m-%d'),
                att.employee.employee_id_number,
                att.employee.full_name,
                att.employee.department.name if att.employee.department else '',
                att.clock_in.strftime('%H:%M:%S') if att.clock_in else '',
                att.clock_out.strftime('%H:%M:%S') if att.clock_out else '',
                att.get_status_display(),
                att.get_entry_source_display(),
                att.ip_address or '',
            ])
        return response

class ExportPayrollCSVView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        filename = f"HRequest_Payroll_Disbursement_Report_{timezone.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Payroll Period', 'Employee ID', 'Employee Name', 'Department', 'Net Salary (PHP)', 'Disbursement Status', 'Released At'])

        for p in PayslipRecord.objects.select_related('employee__department', 'payroll_period').order_by('-payroll_period__period_year', '-payroll_period__period_month'):
            writer.writerow([
                p.payroll_period.label if p.payroll_period else '',
                p.employee.employee_id_number,
                p.employee.full_name,
                p.employee.department.name if p.employee.department else '',
                f"{p.total_salary:.2f}" if p.total_salary else '0.00',
                p.get_status_display(),
                p.uploaded_at.strftime('%Y-%m-%d') if p.uploaded_at else '',
            ])
        return response
