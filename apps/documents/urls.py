from django.urls import path
from .views import (
    SecureDocumentDownloadView,
    EmployeeDocumentUploadView,
    DocumentVaultListView,
)

app_name = 'documents'

urlpatterns = [
    path('vault/', DocumentVaultListView.as_view(), name='vault'),
    path('download/<uuid:pk>/', SecureDocumentDownloadView.as_view(), name='secure_download'),
    path('upload/<uuid:employee_id>/', EmployeeDocumentUploadView.as_view(), name='upload_for_employee'),
]
