from django.urls import path
from .views import (
    MasterPayslipListView,
    PayslipUploadView,
    MyPayslipsView,
    SecurePayslipDownloadView,
)

app_name = 'payslips'

urlpatterns = [
    path('', MasterPayslipListView.as_view(), name='master_list'),
    path('upload/', PayslipUploadView.as_view(), name='upload'),
    path('my/', MyPayslipsView.as_view(), name='my_payslips'),
    path('download/<uuid:pk>/', SecurePayslipDownloadView.as_view(), name='download'),
]
