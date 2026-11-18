from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.storage import private_storage

class AttendanceSource(models.TextChoices):
    WEB = 'WEB', _('Web Portal')
    BIOMETRIC = 'BIOMETRIC', _('Biometric Device')
    MANUAL_CORRECTION = 'MANUAL_CORRECTION', _('Manual Correction')

class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', _('Present')
    LATE = 'LATE', _('Late')
    HALF_DAY = 'HALF_DAY', _('Half Day')
    ABSENT = 'ABSENT', _('Absent')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')
    WFH = 'WFH', _('Work From Home')

class Attendance(models.Model):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text=_('Employee this attendance record belongs to.')
    )
    date = models.DateField(_('date'), db_index=True)
    clock_in = models.DateTimeField(_('clock in time'), null=True, blank=True)
    clock_out = models.DateTimeField(_('clock out time'), null=True, blank=True)
    source = models.CharField(
        _('data source'),
        max_length=20,
        choices=AttendanceSource.choices,
        default=AttendanceSource.WEB
    )
    status = models.CharField(
        _('attendance status'),
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        db_index=True
    )
    is_verified = models.BooleanField(_('verified by HR'), default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_attendances'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    correction_note = models.TextField(_('correction justification'), blank=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        ordering = ['-date', 'employee__last_name']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'date'], name='unique_attendance_per_employee_per_day')
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.get_status_display()})"

    @property
    def total_hours(self):
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            hours = delta.total_seconds() / 3600
            return round(hours, 2)
        return None

    @property
    def status_badge_class(self):
        mapping = {
            AttendanceStatus.PRESENT: 'badge-status-active',
            AttendanceStatus.LATE: 'badge-status-pending',
            AttendanceStatus.HALF_DAY: 'badge-status-pending',
            AttendanceStatus.ABSENT: 'badge-status-terminated',
            AttendanceStatus.ON_LEAVE: 'badge-status-info',
            AttendanceStatus.WFH: 'badge-status-info',
        }
        return mapping.get(self.status, 'badge-status-info')

class ImportBatchStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', _('Pending Review')
    IMPORTED = 'IMPORTED', _('Imported & Applied')
    CANCELLED = 'CANCELLED', _('Cancelled')

class ImportBatch(models.Model):
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='biometric_import_batches'
    )
    import_file = models.FileField(
        storage=private_storage,
        upload_to='biometric_imports/%Y/%m/'
    )
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=ImportBatchStatus.choices,
        default=ImportBatchStatus.PENDING_REVIEW,
        db_index=True
    )
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Biometric Import Batch')
        verbose_name_plural = _('Biometric Import Batches')
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch #{self.id} ({self.original_filename}) - {self.get_status_display()}"

class ImportRowStatus(models.TextChoices):
    VALID = 'VALID', _('Valid')
    DUPLICATE = 'DUPLICATE', _('Duplicate')
    INVALID = 'INVALID', _('Invalid Data')
    CONFLICT = 'CONFLICT', _('Web Conflict')
    IMPORTED = 'IMPORTED', _('Applied')

class ImportRow(models.Model):
    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name='rows'
    )
    row_number = models.PositiveIntegerField()
    raw_data = models.JSONField(default=dict)
    resolved_employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    resolved_date = models.DateField(null=True, blank=True)
    resolved_clock_in = models.DateTimeField(null=True, blank=True)
    resolved_clock_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ImportRowStatus.choices,
        default=ImportRowStatus.VALID
    )
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Import Row')
        verbose_name_plural = _('Import Rows')
        ordering = ['batch', 'row_number']

    def __str__(self):
        return f"Batch #{self.batch_id} Row {self.row_number}: {self.get_status_display()}"
