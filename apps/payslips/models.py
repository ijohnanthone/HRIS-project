import uuid
import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.storage import private_storage

class PayrollPeriod(models.Model):
    label = models.CharField(_('period label'), max_length=50, unique=True, help_text=_('e.g. November 2026'))
    period_month = models.PositiveSmallIntegerField(_('month'), help_text=_('1 to 12'))
    period_year = models.PositiveSmallIntegerField(_('year'), help_text=_('e.g. 2026'))
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Payroll Period')
        verbose_name_plural = _('Payroll Periods')
        ordering = ['-period_year', '-period_month']
        constraints = [
            models.UniqueConstraint(fields=['period_month', 'period_year'], name='unique_payroll_month_year')
        ]

    def __str__(self):
        return self.label

class PayslipStatus(models.TextChoices):
    PAID = 'PAID', _('Paid')
    AVAILABLE = 'AVAILABLE', _('Available')
    NEW = 'NEW', _('New')

class PayslipRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='payslip_records',
        help_text=_('Employee receiving this payslip.')
    )
    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.PROTECT,
        related_name='payslip_records'
    )
    payslip_file = models.FileField(
        _('payslip PDF file'),
        storage=private_storage,
        upload_to='payslips/%Y/%m/'
    )
    file_size = models.PositiveIntegerField(default=0)
    total_salary = models.DecimalField(
        _('total net salary'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Net disbursed salary amount in USD ($)')
    )
    status = models.CharField(
        _('payment status'),
        max_length=20,
        choices=PayslipStatus.choices,
        default=PayslipStatus.PAID
    )
    is_replacement = models.BooleanField(
        _('authorized replacement'),
        default=False,
        help_text=_('Flags whether this is an authorized re-upload replacing a previous release.')
    )
    replacement_note = models.TextField(
        _('replacement audit justification'),
        blank=True,
        help_text=_('Mandatory reason if replacing an already released payslip.')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_payslips'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_released = models.BooleanField(
        _('released to employee'),
        default=True,
        help_text=_('Controls whether the employee can view and download this payslip.')
    )

    class Meta:
        verbose_name = _('Payslip Record')
        verbose_name_plural = _('Payslip Records')
        ordering = ['-payroll_period__period_year', '-payroll_period__period_month', 'employee__last_name']

    def __str__(self):
        return f"{self.employee.full_name} - {self.payroll_period.label}"

    def save(self, *args, **kwargs):
        if self.payslip_file and hasattr(self.payslip_file, 'size') and not self.file_size:
            self.file_size = self.payslip_file.size
        super().save(*args, **kwargs)

    @property
    def status_badge_class(self):
        mapping = {
            PayslipStatus.PAID: 'badge-status-paid',
            PayslipStatus.AVAILABLE: 'badge-status-pending',
            PayslipStatus.NEW: 'badge-status-info',
        }
        return mapping.get(self.status, 'badge-status-info')

    @property
    def formatted_size(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"
