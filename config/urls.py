from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='dashboard'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('org/', include('apps.organizations.urls', namespace='organizations')),
    path('employees/', include('apps.employees.urls', namespace='employees')),
    path('documents/', include('apps.documents.urls', namespace='documents')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('requests/', include('apps.requests.urls', namespace='requests')),
    path('payslips/', include('apps.payslips.urls', namespace='payslips')),
    path('announcements/', include('apps.announcements.urls', namespace='announcements')),
    path('core/', include('apps.core.urls', namespace='core')),
    path('reports/', include('apps.core.urls_reports', namespace='reports')),
    path('system-admin/', include('apps.core.urls_admin', namespace='system_admin')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
