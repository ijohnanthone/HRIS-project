import uuid
import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.storage import private_storage

class DocumentCategory(models.TextChoices):
    CONTRACT = 'CONTRACT', _('Employment Contract')
    GOVERNMENT_ID = 'GOVERNMENT_ID', _('Government Issued ID')
    RESUME = 'RESUME', _('Resume / CV')
    TAX_DOCUMENT = 'TAX_DOCUMENT', _('Tax Form / Document')
    PERFORMANCE_REVIEW = 'PERFORMANCE_REVIEW', _('Performance Review')
    DISCIPLINARY = 'DISCIPLINARY', _('Disciplinary Record')
    OTHER = 'OTHER', _('Other Document')

class EmployeeDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='documents',
        help_text=_('Employee this document belongs to.')
    )
    title = models.CharField(_('document title'), max_length=150)
    category = models.CharField(
        _('category'),
        max_length=30,
        choices=DocumentCategory.choices,
        default=DocumentCategory.CONTRACT
    )
    file = models.FileField(
        _('document file'),
        storage=private_storage,
        upload_to='documents/%Y/%m/'
    )
    file_size = models.PositiveIntegerField(_('file size in bytes'), default=0)
    mime_type = models.CharField(_('MIME type'), max_length=100, blank=True, default='')
    is_confidential = models.BooleanField(
        _('confidential'),
        default=True,
        help_text=_('If true, only HR Admin and Super Admin can view/download this document.')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Employee Document')
        verbose_name_plural = _('Employee Documents')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()}) - {self.employee.full_name}"

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size') and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        if self.file:
            return os.path.splitext(self.file.name)[1].lower().replace('.', '')
        return ''

    @property
    def formatted_size(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"
