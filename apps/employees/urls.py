from django.urls import path
from .views import EmployeeListView, EmployeeDetailView, EmployeeExportCSVView

app_name = 'employees'

urlpatterns = [
    path('', EmployeeListView.as_view(), name='list'),
    path('export/csv/', EmployeeExportCSVView.as_view(), name='export_csv'),
    path('<uuid:pk>/', EmployeeDetailView.as_view(), name='detail'),
]
