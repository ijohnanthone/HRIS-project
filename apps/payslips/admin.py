from django.contrib import admin
from .models import PayrollPeriod, PayslipRecord

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ('label', 'period_month', 'period_year', 'is_active', 'created_at')
    list_filter = ('period_year', 'is_active')

@admin.register(PayslipRecord)
class PayslipRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'payroll_period', 'total_salary', 'status', 'is_replacement', 'uploaded_by', 'uploaded_at')
    list_filter = ('status', 'is_replacement', 'payroll_period')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id_number')
    readonly_fields = ('id', 'uploaded_at')
