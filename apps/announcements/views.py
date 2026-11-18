from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from apps.core.mixins import RoleRequiredMixin
from .models import Announcement, AnnouncementPriority
from .forms import AnnouncementForm

class AnnouncementListView(LoginRequiredMixin, ListView):
    model = Announcement
    template_name = 'announcements/list.html'
    context_object_name = 'announcements'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.filter(is_published=True).select_related('author', 'target_department')

        # Department scoping for employees
        if user.role == 'EMPLOYEE' and hasattr(user, 'employee_profile'):
            dept = user.employee_profile.department
            qs = qs.filter(Q(target_department__isnull=True) | Q(target_department=dept))

        priority = self.request.GET.get('priority', '').strip()
        if priority:
            qs = qs.filter(priority=priority)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['priorities'] = AnnouncementPriority.choices
        context['current_priority'] = self.request.GET.get('priority', '')
        context['can_create'] = self.request.user.is_superuser or self.request.user.role in ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']
        return context

class AnnouncementCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/create.html'
    success_url = reverse_lazy('announcements:list')
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']

    def form_valid(self, form):
        announcement = form.save(commit=False)
        announcement.author = self.request.user
        announcement.is_published = True
        announcement.save()
        messages.success(self.request, f"Announcement '{announcement.title}' published successfully!")
        return super().form_valid(form)

class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    model = Announcement
    template_name = 'announcements/detail.html'
    context_object_name = 'announcement'
