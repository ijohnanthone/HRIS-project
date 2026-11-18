import mimetypes
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View, ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.contrib import messages
from django.urls import reverse
from apps.core.mixins import RoleRequiredMixin
from apps.employees.models import Employee
from .models import EmployeeDocument, DocumentCategory
from .forms import EmployeeDocumentUploadForm

class SecureDocumentDownloadView(LoginRequiredMixin, View):
    """
    Guarded file streaming controller ensuring no confidential document
    is ever downloaded without strict identity and role validation.
    """
    def get(self, request, pk, *args, **kwargs):
        doc = get_object_or_404(EmployeeDocument.objects.select_related('employee__user'), pk=pk)
        user = request.user

        # 1. Super Admin & HR Admin: Unrestricted access
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN']:
            pass
        # 2. HR Staff: Allowed only for non-confidential operational documents
        elif user.role == 'HR_STAFF':
            if doc.is_confidential:
                raise PermissionDenied("Confidential records are restricted from HR Staff access.")
        # 3. Employee: Allowed only for their own non-confidential documents
        elif user.role == 'EMPLOYEE':
            if doc.employee.user_id != user.id:
                raise PermissionDenied("You can only access your own documents.")
            if doc.is_confidential:
                raise PermissionDenied("This document is classified as confidential HR documentation.")
        else:
            raise PermissionDenied("Unauthorized document access.")

        if not doc.file or not doc.file.storage.exists(doc.file.name):
            raise Http404("Document file not found in vault.")

        content_type, _ = mimetypes.guess_type(doc.file.name)
        response = FileResponse(doc.file.open('rb'), content_type=content_type or 'application/octet-stream')
        # inline viewing for PDFs and images, attachment for others
        is_previewable = content_type and ('pdf' in content_type or 'image' in content_type)
        disposition = 'inline' if is_previewable else 'attachment'
        response['Content-Disposition'] = f'{disposition}; filename="{doc.title}.{doc.file_extension}"'
        return response

class EmployeeDocumentUploadView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def post(self, request, employee_id, *args, **kwargs):
        employee = get_object_or_404(Employee, pk=employee_id)
        form = EmployeeDocumentUploadForm(request.POST, request.FILES)

        if form.is_valid():
            doc = form.save(commit=False)
            doc.employee = employee
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, f"Document '{doc.title}' uploaded successfully.")
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())

        return redirect('employees:detail', pk=employee.id)

class DocumentVaultListView(LoginRequiredMixin, ListView):
    model = EmployeeDocument
    template_name = 'documents/vault.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = EmployeeDocument.objects.select_related('employee__department', 'employee__position', 'uploaded_by')

        if user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN']:
            pass
        elif user.role == 'HR_STAFF':
            qs = qs.filter(is_confidential=False)
        else:
            if hasattr(user, 'employee_profile'):
                qs = qs.filter(employee=user.employee_profile, is_confidential=False)
            else:
                qs = qs.none()

        category = self.request.GET.get('category', '').strip()
        if category:
            qs = qs.filter(category=category)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.choices
        context['current_category'] = self.request.GET.get('category', '')
        return context
