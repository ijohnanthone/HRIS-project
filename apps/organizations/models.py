from django.db import models
from django.utils.translation import gettext_lazy as _

class Department(models.Model):
    name = models.CharField(_('department name'), max_length=100, unique=True)
    code = models.CharField(_('department code'), max_length=20, unique=True, db_index=True)
    description = models.TextField(_('description'), blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments',
        help_text=_('Parent department for hierarchical org tree.')
    )
    head_of_department = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        help_text=_('Employee who leads this department.')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_employees(self):
        return self.employees.count()

class Position(models.Model):
    title = models.CharField(_('job title'), max_length=100)
    code = models.CharField(_('position code'), max_length=20, unique=True, db_index=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='positions',
        help_text=_('Department this position belongs to.')
    )
    grade_level = models.CharField(_('grade level'), max_length=20, blank=True, null=True, help_text=_('e.g. L1, L2, L3, Senior, Exec'))
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Position')
        verbose_name_plural = _('Positions')
        ordering = ['department', 'title']
        constraints = [
            models.UniqueConstraint(fields=['title', 'department'], name='unique_position_title_per_department')
        ]

    def __str__(self):
        return f"{self.title} - {self.department.name}"
