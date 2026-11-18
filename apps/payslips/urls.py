from django.urls import path
from .views import (
    PayslipIndexView,
    MasterPayslipListView,
    PayslipUploadView,
    MyPayslipsView,
    SecurePayslipDownloadView,
)

app_name = 'payslips'

urlpatterns = [
    path('', PayslipIndexView.as_view(), name='index'),
    path('master/', MasterPayslipListView.as_view(), name='master_list'),
    path('upload/', PayslipUploadView.as_view(), name='upload'),
    path('my/', MyPayslipsView.as_view(), name='my_payslips'),
    path('download/<uuid:pk>/', SecurePayslipDownloadView.as_view(), name='download'),
]
