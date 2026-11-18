from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Department
from apps.employees.models import Employee

class CompanyStructureView(LoginRequiredMixin, TemplateView):
    template_name = 'organizations/company_structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        departments = Department.objects.prefetch_related('employees__position', 'employees__user', 'positions').all()
        context['departments'] = departments
        context['total_departments'] = departments.count()
        context['total_employees'] = Employee.objects.count()
        return context
