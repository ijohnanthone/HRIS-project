from django.urls import path
from .views import (
    WebClockInOutView,
    AttendanceRosterView,
    MyAttendanceView,
    ManualAttendanceCorrectionView,
    BiometricCSVUploadView,
    BiometricImportPreviewView,
    BiometricImportConfirmView,
    DownloadSampleCSVView,
)

app_name = 'attendance'

urlpatterns = [
    path('', AttendanceRosterView.as_view(), name='roster'),
    path('clock/', WebClockInOutView.as_view(), name='clock_in_out'),
    path('my/', MyAttendanceView.as_view(), name='my_attendance'),
    path('correct/<int:pk>/', ManualAttendanceCorrectionView.as_view(), name='manual_correction'),
    path('import/', BiometricCSVUploadView.as_view(), name='import_upload'),
    path('import/<int:batch_id>/preview/', BiometricImportPreviewView.as_view(), name='import_preview'),
    path('import/<int:batch_id>/confirm/', BiometricImportConfirmView.as_view(), name='import_confirm'),
    path('import/sample-csv/', DownloadSampleCSVView.as_view(), name='download_sample_csv'),
]
