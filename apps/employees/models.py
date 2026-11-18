import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Department, Position

class EmploymentType(models.TextChoices):
    FULL_TIME = 'FULL_TIME', _('Full Time')
    PART_TIME = 'PART_TIME', _('Part Time')
    CONTRACT = 'CONTRACT', _('Contract')
    PROBATIONARY = 'PROBATIONARY', _('Probationary')

class EmployeeStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    ONBOARDING = 'ONBOARDING', _('Onboarding')
    OFFER_PENDING = 'OFFER_PENDING', _('Offer Pending')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')
    TERMINATED = 'TERMINATED', _('Terminated')

class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        help_text=_('Associated system user login account.')
    )
    employee_id_number = models.CharField(
        _('employee ID'),
        max_length=30,
        unique=True,
        db_index=True,
        help_text=_('Unique employee registration number, e.g. 00236 or EMP-2026-001')
    )
    first_name = models.CharField(_('first name'), max_length=50)
    middle_name = models.CharField(_('middle name'), max_length=50, blank=True, default='')
    last_name = models.CharField(_('last name'), max_length=50)

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees',
        help_text=_('Primary department')
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name='employees',
        help_text=_('Assigned job role / title')
    )

    employment_type = models.CharField(
        _('employment type'),
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    status = models.CharField(
        _('employment status'),
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.ACTIVE,
        db_index=True
    )
    work_location = models.CharField(_('work location'), max_length=100, default='Headquarters')

    hire_date = models.DateField(_('date of hire'))
    probation_end_date = models.DateField(_('probation end date'), null=True, blank=True)
    birth_date = models.DateField(_('birth date'), null=True, blank=True)

    phone_number = models.CharField(_('contact phone'), max_length=30, blank=True)
    personal_email = models.EmailField(_('personal email'), blank=True)
    emergency_contact_name = models.CharField(_('emergency contact name'), max_length=100, blank=True)
    emergency_contact_phone = models.CharField(_('emergency contact phone'), max_length=30, blank=True)

    avatar = models.ImageField(upload_to='avatars/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        ordering = ['employee_id_number']

    def __str__(self):
        return f"{self.employee_id_number} - {self.full_name}"

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name[:1]}. {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        f = self.first_name[:1] if self.first_name else ''
        l = self.last_name[:1] if self.last_name else ''
        return f"{f}{l}".upper() or 'EM'

    @property
    def status_badge_class(self):
        mapping = {
            EmployeeStatus.ACTIVE: 'badge-status-active',
            EmployeeStatus.ONBOARDING: 'badge-status-onboarding',
            EmployeeStatus.OFFER_PENDING: 'badge-status-pending',
            EmployeeStatus.ON_LEAVE: 'badge-status-info',
            EmployeeStatus.TERMINATED: 'badge-status-terminated',
        }
        return mapping.get(self.status, 'badge-status-info')
