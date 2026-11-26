from collections import defaultdict
from django.core.paginator import Paginator
from django.db.models import Count, Q, Prefetch
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Department, Position
from apps.employees.models import Employee, EmployeeStatus, WorkLocation


def _parse_per_page(request, default=10):
    raw = request.GET.get('per_page', str(default))
    if raw in ('10', '25', '50'):
        return int(raw)
    return default


def _apply_employee_sort(qs, sort_key):
    mapping = {
        'name': ('first_name', 'last_name'),
        '-name': ('-first_name', '-last_name'),
        'id': ('employee_id_number',),
        '-id': ('-employee_id_number',),
        'position': ('position__title', 'first_name'),
        'department': ('department__name', 'first_name'),
    }
    order = mapping.get(sort_key, ('first_name', 'last_name'))
    return qs.order_by(*order)


class CompanyStructureView(LoginRequiredMixin, TemplateView):
    """
    1. Company Overview:
    Top KPI summary cards + clean, compact Department cards with head photo & overlapping avatar stack.
    """
    template_name = 'organizations/company_structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status=EmployeeStatus.ACTIVE).count()
        inactive_employees = total_employees - active_employees

        departments = (
            Department.objects
            .select_related('head_of_department', 'head_of_department__position')
            .annotate(member_count=Count('employees'))
            .prefetch_related(
                Prefetch(
                    'employees',
                    queryset=Employee.objects.select_related('position').order_by('first_name', 'last_name'),
                    to_attr='ordered_members',
                )
            )
            .order_by('name')
        )

        for dept in departments:
            members = getattr(dept, 'ordered_members', [])
            dept.preview_members = members[:5]
            dept.extra_members_count = max(0, dept.member_count - 5)

        context.update({
            'active_org_tab': 'overview',
            'departments': departments,
            'total_departments': departments.count(),
            'total_employees': total_employees,
            'active_employees': active_employees,
            'inactive_employees': inactive_employees,
        })
        return context


class DepartmentDetailView(LoginRequiredMixin, TemplateView):
    """
    Department Detail View:
    Department Header + Grid View / List View toggle, search, filter, sort, and 10/25/50 pagination.
    """
    template_name = 'organizations/department_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = get_object_or_404(
            Department.objects.select_related('head_of_department', 'head_of_department__position'),
            pk=self.kwargs['pk']
        )

        qs = (
            Employee.objects
            .filter(department=department)
            .select_related('department', 'position', 'manager', 'user')
        )

        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        sort_key = self.request.GET.get('sort', 'name').strip()
        view_mode = self.request.GET.get('view', 'grid').strip()
        if view_mode not in ('grid', 'list'):
            view_mode = 'grid'
        per_page = _parse_per_page(self.request, default=10)

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(middle_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(employee_id_number__icontains=q) |
                Q(position__title__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)

        qs = _apply_employee_sort(qs, sort_key)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(self.request.GET.get('page', 1))

        context.update({
            'active_org_tab': 'overview',
            'department': department,
            'total_dept_employees': Employee.objects.filter(department=department).count(),
            'page_obj': page_obj,
            'employees': page_obj.object_list,
            'view_mode': view_mode,
            'q': q,
            'current_status': status,
            'current_sort': sort_key,
            'per_page': per_page,
            'statuses': EmployeeStatus.choices,
        })
        return context


class OrganizationalChartView(LoginRequiredMixin, TemplateView):
    """
    2. Organizational Chart:
    Builds true reporting hierarchy from Employee.manager relationships in the database.
    """
    template_name = 'organizations/org_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dept_filter = self.request.GET.get('department', '').strip()

        all_emps = list(
            Employee.objects
            .select_related('department', 'position', 'manager')
            .exclude(status=EmployeeStatus.TERMINATED)
            .order_by('first_name', 'last_name')
        )

        if dept_filter:
            filtered_emps = [e for e in all_emps if str(e.department_id) == dept_filter]
        else:
            filtered_emps = all_emps

        emp_ids_in_scope = {e.id for e in filtered_emps}
        children_map = defaultdict(list)
        roots = []

        # Prioritize executives / department heads among root nodes
        headed_ids = set(
            Department.objects.filter(head_of_department__isnull=False)
            .values_list('head_of_department_id', flat=True)
        )

        for emp in filtered_emps:
            if emp.manager_id and emp.manager_id in emp_ids_in_scope:
                children_map[emp.manager_id].append(emp)
            else:
                roots.append(emp)

        def _root_sort_key(e):
            title = (e.position.title or '').lower()
            is_exec = 0 if ('chief' in title or 'ceo' in title or e.department.code == 'DEP-EXEC') else 1
            is_head = 0 if e.id in headed_ids else 1
            return (is_exec, is_head, e.first_name, e.last_name)

        roots.sort(key=_root_sort_key)

        visited = set()

        def build_node(emp):
            if emp.id in visited:
                return None
            visited.add(emp.id)
            child_nodes = []
            for child in children_map.get(emp.id, []):
                cnode = build_node(child)
                if cnode:
                    child_nodes.append(cnode)
            return {
                'employee': emp,
                'children': child_nodes,
                'direct_count': len(child_nodes),
                'is_head': emp.id in headed_ids,
            }

        org_roots = []
        for r in roots:
            node = build_node(r)
            if node:
                org_roots.append(node)

        context.update({
            'active_org_tab': 'org_chart',
            'org_roots': org_roots,
            'departments': Department.objects.order_by('name'),
            'current_department': dept_filter,
            'total_in_chart': len(filtered_emps),
        })
        return context


class EmployeeDirectoryView(LoginRequiredMixin, TemplateView):
    """
    3. Employee Directory:
    Centralized searchable/filterable directory with Grid & List views and pagination.
    """
    template_name = 'organizations/directory.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Employee.objects.select_related('department', 'position', 'manager', 'user').all()

        q = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('department', '').strip()
        pos_id = self.request.GET.get('position', '').strip()
        status = self.request.GET.get('status', '').strip()
        location = self.request.GET.get('location', '').strip()
        sort_key = self.request.GET.get('sort', 'name').strip()
        view_mode = self.request.GET.get('view', 'grid').strip()
        if view_mode not in ('grid', 'list'):
            view_mode = 'grid'
        per_page = _parse_per_page(self.request, default=10)

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(middle_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(employee_id_number__icontains=q) |
                Q(user__email__icontains=q)
            )
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if pos_id:
            qs = qs.filter(position_id=pos_id)
        if status:
            qs = qs.filter(status=status)
        if location:
            qs = qs.filter(work_location=location)

        qs = _apply_employee_sort(qs, sort_key)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(self.request.GET.get('page', 1))

        context.update({
            'active_org_tab': 'directory',
            'page_obj': page_obj,
            'employees': page_obj.object_list,
            'total_filtered': paginator.count,
            'view_mode': view_mode,
            'q': q,
            'current_department': dept_id,
            'current_position': pos_id,
            'current_status': status,
            'current_location': location,
            'current_sort': sort_key,
            'per_page': per_page,
            'departments': Department.objects.order_by('name'),
            'positions': Position.objects.filter(is_active=True).order_by('title'),
            'statuses': EmployeeStatus.choices,
            'locations': WorkLocation.choices,
        })
        return context
