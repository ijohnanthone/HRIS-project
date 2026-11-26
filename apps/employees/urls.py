from django.urls import path
from .views import (
    EmployeeListView,
    EmployeeDetailView,
    EmployeeExportCSVView,
    EmployeeOnboardingWizardView,
    EmployeeTerminateView,
    EmployeeDeleteView,
    EmployeeUpdateView,
)

app_name = 'employees'

urlpatterns = [
    path('', EmployeeListView.as_view(), name='list'),
    path('onboard/', EmployeeOnboardingWizardView.as_view(), {'step': 1}, name='onboard_start'),
    path('onboard/<int:step>/', EmployeeOnboardingWizardView.as_view(), name='onboard_step'),
    path('export/csv/', EmployeeExportCSVView.as_view(), name='export_csv'),
    path('<uuid:pk>/', EmployeeDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', EmployeeUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/terminate/', EmployeeTerminateView.as_view(), name='terminate'),
    path('<uuid:pk>/delete/', EmployeeDeleteView.as_view(), name='delete'),
]
