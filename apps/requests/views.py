import os
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, ListView, DetailView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from apps.core.mixins import RoleRequiredMixin
from apps.employees.models import Employee
from .models import (
    DocumentRequest,
    RequestType,
    RequestStatus,
    FulfillmentMethod,
    COETemplate,
    RequestHistory,
)
from .forms import (
    COERequestSubmissionForm,
    COEApprovalDecisionForm,
    COETemplateForm,
)
from .services.coe_pdf_generator import generate_coe_pdf

class RequestIndexView(LoginRequiredMixin, View):
    """
    Intelligent routing entrypoint for /requests/:
    Redirects HR team to master COE queue and employees to their personal request history.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']:
            return redirect('requests:coe_list')
        return redirect('requests:my_requests')

class COERequestListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    Master queue for HR personnel to review, approve, and fulfill COE requests.
    """
    model = DocumentRequest
    template_name = 'requests/coe_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def get_queryset(self):
        qs = DocumentRequest.objects.select_related('employee__department', 'employee__position', 'approved_by')
        status = self.request.GET.get('status', '').strip()
        req_type = self.request.GET.get('type', '').strip()
        query = self.request.GET.get('q', '').strip()

        if status:
            qs = qs.filter(status=status)
        if req_type:
            qs = qs.filter(request_type=req_type)
        if query:
            qs = qs.filter(
                employee__first_name__icontains=query) | qs.filter(
                employee__last_name__icontains=query) | qs.filter(
                ticket_number__icontains=query
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = RequestStatus.choices
        context['types'] = RequestType.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['pending_count'] = DocumentRequest.objects.filter(status=RequestStatus.PENDING).count()
        return context

class MyCOERequestsView(LoginRequiredMixin, ListView):
    """
    Self-service portal for employees to track and download their COE requests.
    """
    model = DocumentRequest
    template_name = 'requests/my_coe_requests.html'
    context_object_name = 'my_requests'
    paginate_by = 15

    def get_queryset(self):
        if not hasattr(self.request.user, 'employee_profile'):
            return DocumentRequest.objects.none()
        return DocumentRequest.objects.filter(employee=self.request.user.employee_profile).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = COERequestSubmissionForm()
        return context

class COERequestCreateView(LoginRequiredMixin, View):
    """
    Submits a new COE request on behalf of the signed-in employee.
    """
    def post(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'employee_profile'):
            messages.error(request, "Only registered employees with an active profile can submit COE requests.")
            return redirect('dashboard')

        form = COERequestSubmissionForm(request.POST)
        if form.is_valid():
            coe_req = form.save(commit=False)
            coe_req.employee = user.employee_profile
            coe_req.ticket_number = DocumentRequest.generate_ticket_number()
            coe_req.status = RequestStatus.PENDING
            coe_req.save()

            # Create history record
            RequestHistory.objects.create(
                request=coe_req,
                actor=user,
                action='SUBMITTED',
                from_status='',
                to_status=RequestStatus.PENDING,
                remarks=f"Request submitted with stated purpose: {coe_req.purpose}"
            )

            # Sync real-time event to Firebase Realtime Database (no-ops if unconfigured)
            from apps.core.firebase_admin_helper import push_realtime_event
            push_realtime_event('hr_requests', {
                'ticket_number': coe_req.ticket_number,
                'employee': coe_req.employee.full_name,
                'request_type': coe_req.get_request_type_display(),
                'status': coe_req.get_status_display(),
                'created_at': timezone.now().isoformat(),
            })

            messages.success(request, f"COE Request {coe_req.ticket_number} submitted successfully! Your HR team will review it shortly.")
            return redirect('requests:my_requests')

        for error in form.errors.values():
            messages.error(request, error.as_text())
        return redirect('requests:my_requests')

class COERequestDetailView(LoginRequiredMixin, DetailView):
    """
    Ticket inspection view with approval/rejection decision controls for HR Admins.
    """
    model = DocumentRequest
    template_name = 'requests/coe_detail.html'
    context_object_name = 'coe'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        # Strict authorization: Only HR team or the owner employee can view
        if user.role == 'EMPLOYEE' and not user.is_superuser:
            if not hasattr(user, 'employee_profile') or obj.employee_id != user.employee_profile.id:
                raise PermissionDenied("You can only inspect your own COE tickets.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_approve'] = user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN']
        context['approval_form'] = COEApprovalDecisionForm()
        context['history'] = self.object.history.select_related('actor').all()
        return context

class COEApprovalProcessView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Single approval executor: Approves (auto PDF / manual PDF) or rejects ticket.
    """
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def post(self, request, pk, *args, **kwargs):
        coe = get_object_or_404(DocumentRequest, pk=pk)
        if coe.status != RequestStatus.PENDING:
            messages.warning(request, f"Ticket {coe.ticket_number} has already been evaluated ({coe.get_status_display()}).")
            return redirect('requests:coe_detail', pk=coe.id)

        form = COEApprovalDecisionForm(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors.values():
                messages.error(request, error.as_text())
            return redirect('requests:coe_detail', pk=coe.id)

        decision = form.cleaned_data['decision']
        now = timezone.now()

        if decision == 'REJECT':
            reason = form.cleaned_data['rejection_reason']
            coe.status = RequestStatus.REJECTED
            coe.approved_by = request.user
            coe.approved_at = now
            coe.rejection_reason = reason
            coe.save()

            RequestHistory.objects.create(
                request=coe,
                actor=request.user,
                action='REJECTED',
                from_status=RequestStatus.PENDING,
                to_status=RequestStatus.REJECTED,
                remarks=f"Rejected by HR: {reason}"
            )
            messages.info(request, f"COE Request {coe.ticket_number} has been rejected.")

        elif decision == 'APPROVE_AUTO':
            # 1. Fetch active template
            template = COETemplate.objects.filter(is_active=True).first()

            # 2. Generate PDF in memory via ReportLab
            pdf_bytes = generate_coe_pdf(coe, template)
            filename = f"COE_{coe.ticket_number}_{coe.employee.employee_id_number}.pdf"

            coe.generated_document.save(filename, ContentFile(pdf_bytes), save=False)
            coe.status = RequestStatus.FULFILLED
            coe.approved_by = request.user
            coe.approved_at = now
            coe.fulfillment_method = FulfillmentMethod.AUTO_GENERATED
            coe.document_released_at = now
            coe.save()

            RequestHistory.objects.create(
                request=coe,
                actor=request.user,
                action='APPROVED_AND_FULFILLED',
                from_status=RequestStatus.PENDING,
                to_status=RequestStatus.FULFILLED,
                remarks="Approved and automatically compiled official PDF certificate."
            )
            messages.success(request, f"COE {coe.ticket_number} approved and official PDF certificate successfully generated!")

        elif decision == 'APPROVE_MANUAL':
            signed_file = form.cleaned_data['signed_pdf']
            coe.generated_document.save(signed_file.name, signed_file, save=False)
            coe.status = RequestStatus.FULFILLED
            coe.approved_by = request.user
            coe.approved_at = now
            coe.fulfillment_method = FulfillmentMethod.MANUAL_UPLOAD
            coe.document_released_at = now
            coe.save()

            RequestHistory.objects.create(
                request=coe,
                actor=request.user,
                action='APPROVED_AND_FULFILLED',
                from_status=RequestStatus.PENDING,
                to_status=RequestStatus.FULFILLED,
                remarks=f"Approved with manual pre-signed document: {signed_file.name}"
            )
            messages.success(request, f"COE {coe.ticket_number} approved and signed document uploaded successfully!")

        return redirect('requests:coe_detail', pk=coe.id)

class COEDocumentDownloadView(LoginRequiredMixin, View):
    """
    Secure download controller for issued Certificate of Employment.
    Guarantees no unapproved or non-owned certificate can ever be downloaded.
    """
    def get(self, request, pk, *args, **kwargs):
        coe = get_object_or_404(DocumentRequest.objects.select_related('employee__user'), pk=pk)
        user = request.user

        # 1. Ticket must be fulfilled/completed
        if coe.status != RequestStatus.FULFILLED or not coe.generated_document:
            raise PermissionDenied("No certificate has been approved or released for this ticket yet.")

        # 2. Authorization check
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']:
            pass
        elif user.role == 'EMPLOYEE':
            if coe.employee.user_id != user.id:
                raise PermissionDenied("You can only access your own employment certificates.")
        else:
            raise PermissionDenied("Unauthorized certificate access.")

        if not coe.generated_document.storage.exists(coe.generated_document.name):
            raise Http404("Certificate file not found in storage.")

        content_type, _ = mimetypes.guess_type(coe.generated_document.name)
        response = FileResponse(coe.generated_document.open('rb'), content_type=content_type or 'application/pdf')
        response['Content-Disposition'] = f'inline; filename="Certificate_of_Employment_{coe.ticket_number}.pdf"'
        return response

class COETemplateManageView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    View to inspect and manage active COE templates.
    """
    template_name = 'requests/coe_templates.html'
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = COETemplate.objects.all()
        context['form'] = COETemplateForm()
        return context
