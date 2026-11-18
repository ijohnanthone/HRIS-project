import uuid
import datetime
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.storage import private_storage

class TemplateType(models.TextChoices):
    WITH_COMPENSATION = 'WITH_COMPENSATION', _('With Compensation Details')
    WITHOUT_COMPENSATION = 'WITHOUT_COMPENSATION', _('Without Compensation Details')
    GENERAL = 'GENERAL', _('General Employment Certification')

class COETemplate(models.Model):
    name = models.CharField(_('template name'), max_length=150)
    template_type = models.CharField(
        _('template type'),
        max_length=30,
        choices=TemplateType.choices,
        default=TemplateType.WITHOUT_COMPENSATION,
        db_index=True
    )
    header_title = models.CharField(
        _('header title'),
        max_length=200,
        default='CERTIFICATE OF EMPLOYMENT'
    )
    body_template = models.TextField(
        _('body text template'),
        help_text=_(
            'Placeholders supported: {employee_name}, {position}, {department}, '
            '{hire_date}, {monthly_salary}, {work_location}, {issue_date}, {purpose}'
        )
    )
    signatory_name = models.CharField(_('signatory name'), max_length=100, default='Paula Mora')
    signatory_title = models.CharField(_('signatory title'), max_length=100, default='Human Resources Manager')
    is_active = models.BooleanField(_('is active'), default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('COE Template')
        verbose_name_plural = _('COE Templates')
        ordering = ['-is_active', 'name']

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({self.get_template_type_display()}) [{status}]"

class RequestType(models.TextChoices):
    COE_WITH_COMPENSATION = 'COE_WITH_COMPENSATION', _('COE with Compensation')
    COE_WITHOUT_COMPENSATION = 'COE_WITHOUT_COMPENSATION', _('COE without Compensation')

class RequestStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    FULFILLED = 'FULFILLED', _('Completed & Released')

class FulfillmentMethod(models.TextChoices):
    AUTO_GENERATED = 'AUTO_GENERATED', _('Auto Generated PDF')
    MANUAL_UPLOAD = 'MANUAL_UPLOAD', _('Manual PDF Upload')

class DocumentRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(_('ticket number'), max_length=30, unique=True, db_index=True)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='document_requests'
    )
    request_type = models.CharField(
        _('request type'),
        max_length=30,
        choices=RequestType.choices,
        default=RequestType.COE_WITHOUT_COMPENSATION
    )
    purpose = models.TextField(
        _('purpose of request'),
        help_text=_('State purpose (e.g. Visa application, bank loan, credit card, housing requirement)...')
    )
    status = models.CharField(
        _('ticket status'),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        db_index=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_coe_requests'
    )
    approved_at = models.DateTimeField(_('approval timestamp'), null=True, blank=True)
    rejection_reason = models.TextField(_('rejection reason'), blank=True)

    fulfillment_method = models.CharField(
        _('fulfillment method'),
        max_length=20,
        choices=FulfillmentMethod.choices,
        null=True,
        blank=True
    )
    generated_document = models.FileField(
        _('issued certificate PDF'),
        storage=private_storage,
        upload_to='issued_coe/%Y/%m/',
        null=True,
        blank=True
    )
    document_released_at = models.DateTimeField(_('release timestamp'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('COE Request')
        verbose_name_plural = _('COE Requests')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_number} - {self.employee.full_name} ({self.get_status_display()})"

    @property
    def status_badge_class(self):
        mapping = {
            RequestStatus.PENDING: 'badge-status-pending',
            RequestStatus.APPROVED: 'badge-status-active',
            RequestStatus.REJECTED: 'badge-status-terminated',
            RequestStatus.FULFILLED: 'badge-status-approved',
        }
        return mapping.get(self.status, 'badge-status-info')

    @classmethod
    def generate_ticket_number(cls):
        count = cls.objects.count() + 1
        year = settings.TIME_ZONE
        return f"COE-{datetime.datetime.now().year}-{count:04d}"

class RequestHistory(models.Model):
    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name='history'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=50)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Request History Event')
        verbose_name_plural = _('Request History Events')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.request.ticket_number} - {self.action} at {self.timestamp}"
