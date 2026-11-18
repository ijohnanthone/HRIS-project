from django.contrib import admin
from .models import Attendance, ImportBatch, ImportRow

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'clock_in', 'clock_out', 'source', 'status', 'is_verified')
    list_filter = ('source', 'status', 'is_verified', 'date')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id_number')

@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_filename', 'imported_by', 'status', 'total_rows', 'valid_rows', 'created_at')
    list_filter = ('status', 'created_at')

@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ('batch', 'row_number', 'resolved_employee', 'resolved_date', 'status')
    list_filter = ('status',)
