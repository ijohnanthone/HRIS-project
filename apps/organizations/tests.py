from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position

class OrganizationModelTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(
            name='Engineering',
            code='DEP-ENG',
            description='Tech team'
        )

    def test_department_creation(self):
        self.assertEqual(self.dept.name, 'Engineering')
        self.assertEqual(self.dept.code, 'DEP-ENG')
        self.assertEqual(str(self.dept), 'Engineering (DEP-ENG)')

    def test_unique_department_code(self):
        with self.assertRaises(IntegrityError):
            Department.objects.create(name='Other', code='DEP-ENG')

    def test_position_creation(self):
        pos = Position.objects.create(
            title='Software Engineer',
            code='POS-SWE',
            department=self.dept,
            grade_level='L3'
        )
        self.assertEqual(pos.title, 'Software Engineer')
        self.assertEqual(pos.department, self.dept)
        self.assertEqual(str(pos), 'Software Engineer - Engineering')

    def test_company_structure_view_authenticated(self):
        user = CustomUser.objects.create_user(
            email='test@hrequest.com',
            password='TestPassword2026!'
        )
        client = Client()
        client.login(email='test@hrequest.com', password='TestPassword2026!')
        response = client.get(reverse('organizations:company_structure'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Company Structure')
        self.assertContains(response, 'Engineering')

    def test_department_detail_grid_and_list_views(self):
        import datetime
        from apps.employees.models import Employee, EmployeeStatus

        pos = Position.objects.create(title='Engineer', code='POS-ENG-1', department=self.dept)
        u1 = CustomUser.objects.create_user(email='mgr@hrequest.com', password='Pwd!')
        mgr = Employee.objects.create(
            user=u1, employee_id_number='E-001', first_name='Alice', last_name='Boss',
            department=self.dept, position=pos, hire_date=datetime.date(2024, 1, 1),
            status=EmployeeStatus.ACTIVE,
        )
        self.dept.head_of_department = mgr
        self.dept.save()

        u2 = CustomUser.objects.create_user(email='sub@hrequest.com', password='Pwd!')
        Employee.objects.create(
            user=u2, employee_id_number='E-002', first_name='Bob', last_name='Dev',
            department=self.dept, position=pos, manager=mgr, hire_date=datetime.date(2024, 2, 1),
            status=EmployeeStatus.ACTIVE,
        )

        client = Client()
        client.login(email='mgr@hrequest.com', password='Pwd!')

        res_grid = client.get(reverse('organizations:department_detail', kwargs={'pk': self.dept.id}) + '?view=grid&per_page=25')
        self.assertEqual(res_grid.status_code, 200)
        self.assertContains(res_grid, 'Alice Boss')
        self.assertContains(res_grid, 'Bob Dev')

        res_list = client.get(reverse('organizations:department_detail', kwargs={'pk': self.dept.id}) + '?view=list&q=Bob')
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, 'Bob Dev')
        self.assertContains(res_list, 'Alice Boss')  # shown in Manager column

    def test_org_chart_uses_actual_manager_hierarchy(self):
        import datetime
        from apps.employees.models import Employee

        pos_ceo = Position.objects.create(title='CEO', code='POS-CEO-T', department=self.dept)
        pos_dev = Position.objects.create(title='Developer', code='POS-DEV-T', department=self.dept)
        u_ceo = CustomUser.objects.create_user(email='ceo_t@hrequest.com', password='Pwd!')
        ceo = Employee.objects.create(
            user=u_ceo, employee_id_number='T-001', first_name='Chief', last_name='Exec',
            department=self.dept, position=pos_ceo, hire_date=datetime.date(2022, 1, 1),
        )
        u_dev = CustomUser.objects.create_user(email='dev_t@hrequest.com', password='Pwd!')
        Employee.objects.create(
            user=u_dev, employee_id_number='T-002', first_name='Sub', last_name='Worker',
            department=self.dept, position=pos_dev, manager=ceo, hire_date=datetime.date(2023, 1, 1),
        )

        client = Client()
        client.login(email='ceo_t@hrequest.com', password='Pwd!')
        res = client.get(reverse('organizations:org_chart'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Chief Exec')
        self.assertContains(res, 'Sub Worker')
        self.assertContains(res, '1 report')

    def test_employee_directory_filters_and_pagination(self):
        import datetime
        from apps.employees.models import Employee, WorkLocation

        pos = Position.objects.create(title='Analyst', code='POS-AN-T', department=self.dept)
        u = CustomUser.objects.create_user(email='an@hrequest.com', password='Pwd!')
        Employee.objects.create(
            user=u, employee_id_number='DIR-01', first_name='Clara', last_name='Analyst',
            department=self.dept, position=pos, work_location=WorkLocation.CEBU,
            hire_date=datetime.date(2024, 5, 1),
        )

        client = Client()
        client.login(email='an@hrequest.com', password='Pwd!')
        res = client.get(reverse('organizations:directory') + f'?location={WorkLocation.CEBU}&view=list')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Clara Analyst')
        self.assertContains(res, 'DIR-01')
