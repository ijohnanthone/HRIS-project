from django.urls import path
from .views import (
    CompanyStructureView,
    DepartmentDetailView,
    OrganizationalChartView,
    EmployeeDirectoryView,
)

app_name = 'organizations'

urlpatterns = [
    path('structure/', CompanyStructureView.as_view(), name='company_structure'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='department_detail'),
    path('org-chart/', OrganizationalChartView.as_view(), name='org_chart'),
    path('directory/', EmployeeDirectoryView.as_view(), name='directory'),
]
