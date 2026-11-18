from django.contrib import admin
from .models import DocumentRequest, COETemplate, RequestHistory

@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'employee', 'request_type', 'status', 'approved_by', 'approved_at', 'created_at')
    list_filter = ('status', 'request_type', 'created_at')
    search_fields = ('ticket_number', 'employee__first_name', 'employee__last_name', 'purpose')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(COETemplate)
class COETemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'signatory_name', 'is_active', 'updated_at')
    list_filter = ('template_type', 'is_active')

@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ('request', 'action', 'actor', 'from_status', 'to_status', 'timestamp')
    readonly_fields = ('timestamp',)
