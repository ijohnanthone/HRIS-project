from django.contrib import admin
from .models import EmployeeDocument

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'category', 'file_size', 'is_confidential', 'uploaded_by', 'created_at')
    list_filter = ('category', 'is_confidential', 'created_at')
    search_fields = ('title', 'employee__first_name', 'employee__last_name', 'employee__employee_id_number')
    readonly_fields = ('id', 'file_size', 'created_at')
