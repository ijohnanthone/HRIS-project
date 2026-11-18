import csv
import io
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q
from apps.core.mixins import RoleRequiredMixin
from apps.employees.models import Employee
from apps.organizations.models import Department
from .models import (
    Attendance,
    AttendanceSource,
    AttendanceStatus,
    ImportBatch,
    ImportBatchStatus,
    ImportRow,
    ImportRowStatus,
)
from .forms import ManualAttendanceCorrectionForm, BiometricCSVUploadForm

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

class WebClockInOutView(LoginRequiredMixin, View):
    """
    Handles employee web punch-in and punch-out.
    Enforces duplicate prevention and automated status calculation.
    """
    def post(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'employee_profile'):
            messages.error(request, "Only registered employees with an active profile can clock in/out.")
            return redirect('dashboard')

        employee = user.employee_profile
        now = timezone.now()
        today = now.date()
        action = request.POST.get('action')
        ip_addr = get_client_ip(request)

        # Retrieve or create today's record
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'source': AttendanceSource.WEB,
                'ip_address': ip_addr,
            }
        )

        if action == 'clock_in':
            if attendance.clock_in and not created:
                messages.warning(
                    request,
                    f"You have already clocked in today at {attendance.clock_in.strftime('%I:%M %p')}."
                )
            else:
                attendance.clock_in = now
                attendance.source = AttendanceSource.WEB
                attendance.ip_address = ip_addr

                # Policy: Company work starts at 8:00 AM with 15-min grace period (8:15 AM)
                local_time = timezone.localtime(now).time()
                cutoff_time = datetime.time(8, 15)

                if local_time > cutoff_time:
                    attendance.status = AttendanceStatus.LATE
                else:
                    attendance.status = AttendanceStatus.PRESENT

                attendance.save()
                messages.success(
                    request,
                    f"Clocked in successfully at {timezone.localtime(now).strftime('%I:%M %p')}. Status: {attendance.get_status_display()}."
                )

        elif action == 'clock_out':
            if not attendance.clock_in:
                messages.error(request, "You cannot clock out without first clocking in for today.")
            elif attendance.clock_out:
                messages.warning(
                    request,
                    f"You have already clocked out today at {timezone.localtime(attendance.clock_out).strftime('%I:%M %p')}."
                )
            else:
                attendance.clock_out = now
                # Half-day check: If total duration worked is less than 4 hours
                hours = (attendance.clock_out - attendance.clock_in).total_seconds() / 3600
                if hours < 4.0:
                    attendance.status = AttendanceStatus.HALF_DAY

                attendance.save()
                messages.success(
                    request,
                    f"Clocked out successfully at {timezone.localtime(now).strftime('%I:%M %p')}. Total: {round(hours, 2)} hours."
                )

        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

class AttendanceIndexView(LoginRequiredMixin, View):
    """
    Intelligent routing for /attendance/:
    Redirects HR team to master attendance roster, and employees to personal attendance.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']:
            return redirect('attendance:roster')
        return redirect('attendance:my_attendance')

class AttendanceRosterView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    Master attendance roster for HR team.
    """
    model = Attendance
    template_name = 'attendance/roster.html'
    context_object_name = 'attendances'
    paginate_by = 25
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get_queryset(self):
        qs = Attendance.objects.select_related('employee__department', 'employee__position', 'verified_by')
        date_filter = self.request.GET.get('date', '').strip()
        dept_id = self.request.GET.get('department', '').strip()
        status = self.request.GET.get('status', '').strip()
        query = self.request.GET.get('q', '').strip()

        if date_filter:
            qs = qs.filter(date=date_filter)

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
        context['departments'] = Department.objects.all()
        context['statuses'] = AttendanceStatus.choices
        context['current_date'] = self.request.GET.get('date', '')
        context['current_dept'] = self.request.GET.get('department', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_q'] = self.request.GET.get('q', '')
        context['today'] = timezone.now().date().strftime('%Y-%m-%d')
        return context

class MyAttendanceView(LoginRequiredMixin, ListView):
    """
    Personal attendance record view for employees.
    """
    model = Attendance
    template_name = 'attendance/my_attendance.html'
    context_object_name = 'attendances'
    paginate_by = 31

    def get_queryset(self):
        if not hasattr(self.request.user, 'employee_profile'):
            return Attendance.objects.none()
        emp = self.request.user.employee_profile
        qs = Attendance.objects.filter(employee=emp).order_by('-date')

        month = self.request.GET.get('month')
        if month:
            try:
                dt = datetime.datetime.strptime(month, '%Y-%m')
                qs = qs.filter(date__year=dt.year, date__month=dt.month)
            except ValueError:
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        today_record = None
        if hasattr(self.request.user, 'employee_profile'):
            today_record = Attendance.objects.filter(employee=self.request.user.employee_profile, date=today).first()

        context['today_record'] = today_record
        context['today'] = today
        return context

class ManualAttendanceCorrectionView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Enables authorized HR personnel to correct check-in/out times with mandatory audit note.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def post(self, request, pk, *args, **kwargs):
        attendance = get_object_or_404(Attendance, pk=pk)
        form = ManualAttendanceCorrectionForm(request.POST, instance=attendance)

        if form.is_valid():
            record = form.save(commit=False)
            record.source = AttendanceSource.MANUAL_CORRECTION
            record.is_verified = True
            record.verified_by = request.user
            record.verified_at = timezone.now()
            record.save()
            messages.success(request, f"Attendance for {record.employee.full_name} on {record.date} adjusted successfully.")
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())

        return redirect(request.META.get('HTTP_REFERER', 'attendance:roster'))

class BiometricCSVUploadView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Upload and parse biometric CSV records into an ImportBatch for review.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']
    template_name = 'attendance/import_upload.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {
            'form': BiometricCSVUploadForm()
        })

    def post(self, request, *args, **kwargs):
        form = BiometricCSVUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        uploaded_file = form.cleaned_data['csv_file']
        batch = ImportBatch.objects.create(
            imported_by=request.user,
            import_file=uploaded_file,
            original_filename=uploaded_file.name,
            status=ImportBatchStatus.PENDING_REVIEW
        )

        try:
            # Parse CSV contents
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))

            row_num = 1
            valid_count = 0
            duplicate_count = 0
            error_count = 0

            for row in reader:
                row_num += 1
                emp_id_str = row.get('employee_id', '').strip()
                date_str = row.get('date', '').strip()
                in_str = row.get('clock_in', '').strip()
                out_str = row.get('clock_out', '').strip()

                import_row = ImportRow(
                    batch=batch,
                    row_number=row_num,
                    raw_data=dict(row)
                )

                # Validation 1: Resolve employee
                employee = Employee.objects.filter(employee_id_number=emp_id_str).first()
                if not employee:
                    import_row.status = ImportRowStatus.INVALID
                    import_row.error_message = f"Employee with ID '{emp_id_str}' does not exist."
                    error_count += 1
                    import_row.save()
                    continue

                import_row.resolved_employee = employee

                # Validation 2: Parse date
                try:
                    resolved_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    import_row.resolved_date = resolved_date
                except ValueError:
                    import_row.status = ImportRowStatus.INVALID
                    import_row.error_message = f"Invalid date format '{date_str}', expected YYYY-MM-DD."
                    error_count += 1
                    import_row.save()
                    continue

                # Validation 3: Parse timestamps
                try:
                    if in_str:
                        dt_in = datetime.datetime.strptime(f"{date_str} {in_str}", '%Y-%m-%d %H:%M:%S')
                        import_row.resolved_clock_in = timezone.make_aware(dt_in)
                    if out_str:
                        dt_out = datetime.datetime.strptime(f"{date_str} {out_str}", '%Y-%m-%d %H:%M:%S')
                        import_row.resolved_clock_out = timezone.make_aware(dt_out)
                except ValueError:
                    import_row.status = ImportRowStatus.INVALID
                    import_row.error_message = f"Invalid time format in '{in_str}' or '{out_str}', expected HH:MM:SS."
                    error_count += 1
                    import_row.save()
                    continue

                # Validation 4: Check conflict / duplicate with existing database records
                existing = Attendance.objects.filter(employee=employee, date=resolved_date).first()
                if existing:
                    if existing.source == AttendanceSource.WEB:
                        import_row.status = ImportRowStatus.CONFLICT
                        import_row.error_message = f"Existing web punch on {resolved_date} found. Biometric import will reconcile/overwrite."
                    else:
                        import_row.status = ImportRowStatus.DUPLICATE
                        import_row.error_message = f"Record already imported for {resolved_date}."
                        duplicate_count += 1
                else:
                    import_row.status = ImportRowStatus.VALID
                    valid_count += 1

                import_row.save()

            # Update batch metrics
            batch.total_rows = row_num - 1
            batch.valid_rows = valid_count
            batch.duplicate_rows = duplicate_count
            batch.error_rows = error_count
            batch.save()

            return redirect('attendance:import_preview', batch_id=batch.id)

        except Exception as e:
            batch.status = ImportBatchStatus.CANCELLED
            batch.save()
            messages.error(request, f"Failed to process CSV: {str(e)}")
            return redirect('attendance:import_upload')

class BiometricImportPreviewView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    Displays row-by-row validation report before user confirms import.
    """
    template_name = 'attendance/import_preview.html'
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        batch = get_object_or_404(ImportBatch, pk=self.kwargs['batch_id'])
        context['batch'] = batch
        context['rows'] = batch.rows.select_related('resolved_employee').all()
        return context

class BiometricImportConfirmView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Commits valid and conflict records from the preview batch into the Attendance table.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def post(self, request, batch_id, *args, **kwargs):
        batch = get_object_or_404(ImportBatch, pk=batch_id)
        action = request.POST.get('action')

        if action == 'cancel':
            batch.status = ImportBatchStatus.CANCELLED
            batch.save()
            messages.info(request, f"Biometric Import Batch #{batch.id} was cancelled.")
            return redirect('attendance:roster')

        applied_count = 0
        with transaction.atomic():
            # Import both VALID and CONFLICT rows (biometric reconciles/overwrites existing)
            rows = batch.rows.filter(status__in=[ImportRowStatus.VALID, ImportRowStatus.CONFLICT])

            for r in rows:
                attendance, created = Attendance.objects.get_or_create(
                    employee=r.resolved_employee,
                    date=r.resolved_date,
                    defaults={
                        'clock_in': r.resolved_clock_in,
                        'clock_out': r.resolved_clock_out,
                        'source': AttendanceSource.BIOMETRIC,
                        'is_verified': True,
                        'verified_by': request.user,
                        'verified_at': timezone.now(),
                    }
                )

                if not created:
                    attendance.clock_in = r.resolved_clock_in or attendance.clock_in
                    attendance.clock_out = r.resolved_clock_out or attendance.clock_out
                    attendance.source = AttendanceSource.BIOMETRIC
                    attendance.is_verified = True
                    attendance.verified_by = request.user
                    attendance.verified_at = timezone.now()

                # Status calculation
                if attendance.clock_in:
                    local_in = timezone.localtime(attendance.clock_in).time()
                    if local_in > datetime.time(8, 15):
                        attendance.status = AttendanceStatus.LATE
                    else:
                        attendance.status = AttendanceStatus.PRESENT

                if attendance.clock_in and attendance.clock_out:
                    duration = (attendance.clock_out - attendance.clock_in).total_seconds() / 3600
                    if duration < 4.0:
                        attendance.status = AttendanceStatus.HALF_DAY

                attendance.save()
                r.status = ImportRowStatus.IMPORTED
                r.save()
                applied_count += 1

            batch.status = ImportBatchStatus.IMPORTED
            batch.confirmed_at = timezone.now()
            batch.save()

        messages.success(request, f"Successfully imported and applied {applied_count} biometric attendance records!")
        return redirect('attendance:roster')

class DownloadSampleCSVView(View):
    """
    Downloads a reference biometric CSV template.
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="hrequest_biometric_sample.csv"'
        writer = csv.writer(response)
        writer.writerow(['employee_id', 'date', 'clock_in', 'clock_out'])
        writer.writerow(['00230', timezone.now().date().strftime('%Y-%m-%d'), '08:02:00', '17:05:00'])
        writer.writerow(['00236', timezone.now().date().strftime('%Y-%m-%d'), '08:25:00', '17:30:00'])
        writer.writerow(['00235', timezone.now().date().strftime('%Y-%m-%d'), '08:00:00', '12:00:00'])
        return response
