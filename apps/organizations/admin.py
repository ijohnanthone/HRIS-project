from django.contrib import admin
from .models import Department, Position

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'parent', 'head_of_department', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('parent',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'department', 'grade_level', 'is_active')
    search_fields = ('title', 'code')
    list_filter = ('department', 'is_active', 'grade_level')
