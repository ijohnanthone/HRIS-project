from django.urls import path
from .views_reports import (
    ReportsDashboardView,
    ExportWorkforceCSVView,
    ExportAttendanceCSVView,
    ExportPayrollCSVView,
)

app_name = 'reports'

urlpatterns = [
    path('', ReportsDashboardView.as_view(), name='dashboard'),
    path('export/workforce/', ExportWorkforceCSVView.as_view(), name='export_workforce'),
    path('export/attendance/', ExportAttendanceCSVView.as_view(), name='export_attendance'),
    path('export/payroll/', ExportPayrollCSVView.as_view(), name='export_payroll'),
]
