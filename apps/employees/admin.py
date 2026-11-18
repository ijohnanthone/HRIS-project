from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id_number', 'full_name', 'department', 'position', 'employment_type', 'status', 'hire_date')
    search_fields = ('employee_id_number', 'first_name', 'last_name', 'user__email')
    list_filter = ('status', 'employment_type', 'department', 'work_location')
    readonly_fields = ('id', 'created_at', 'updated_at')
