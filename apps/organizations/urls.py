from django.urls import path
from .views import CompanyStructureView

app_name = 'organizations'

urlpatterns = [
    path('structure/', CompanyStructureView.as_view(), name='company_structure'),
]
