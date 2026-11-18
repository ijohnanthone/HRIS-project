from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class AnnouncementPriority(models.TextChoices):
    NORMAL = 'NORMAL', _('Normal')
    HIGH = 'HIGH', _('High Priority')
    CRITICAL = 'CRITICAL', _('Critical / Urgent')

class Announcement(models.Model):
    title = models.CharField(_('announcement title'), max_length=255)
    content = models.TextField(_('announcement body'))
    priority = models.CharField(
        _('priority level'),
        max_length=20,
        choices=AnnouncementPriority.choices,
        default=AnnouncementPriority.NORMAL,
        db_index=True
    )
    target_department = models.ForeignKey(
        'organizations.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        help_text=_('Leave blank to broadcast to all departments company-wide.')
    )
    is_pinned = models.BooleanField(
        _('pin to top'),
        default=False,
        help_text=_('Pinned announcements appear prominently at the top of the feed and dashboard.')
    )
    is_published = models.BooleanField(_('published'), default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='authored_announcements'
    )
    published_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Announcement')
        verbose_name_plural = _('Announcements')
        ordering = ['-is_pinned', '-published_at']

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title}"

    @property
    def priority_badge_class(self):
        mapping = {
            AnnouncementPriority.NORMAL: 'badge-status-info',
            AnnouncementPriority.HIGH: 'badge-status-pending',
            AnnouncementPriority.CRITICAL: 'badge-status-terminated',
        }
        return mapping.get(self.priority, 'badge-status-info')
