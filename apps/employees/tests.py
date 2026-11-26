import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus

class EmployeeModelAndViewsTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Marketing', code='DEP-MKT')
        self.pos = Position.objects.create(title='Marketing Lead', code='POS-MKT-LD', department=self.dept)

        # HR Admin user
        self.hr_user = CustomUser.objects.create_user(
            email='hr_admin@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.HR_ADMIN,
            is_staff=True
        )

        # Regular employee user
        self.emp_user = CustomUser.objects.create_user(
            email='regular_emp@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )

        self.employee = Employee.objects.create(
            user=self.emp_user,
            employee_id_number='EMP-001',
            first_name='John',
            last_name='Doe',
            department=self.dept,
            position=self.pos,
            employment_type=EmploymentType.FULL_TIME,
            status=EmployeeStatus.ACTIVE,
            work_location='New York',
            hire_date=datetime.date(2024, 1, 1),
            phone_number='+1 555-0100'
        )

    def test_employee_properties(self):
        self.assertEqual(self.employee.full_name, 'John Doe')
        self.assertEqual(self.employee.initials, 'JD')
        self.assertEqual(str(self.employee), 'EMP-001 - John Doe')
        self.assertEqual(self.employee.status_badge_class, 'badge-status-active')

    def test_unique_employee_id_number(self):
        other_user = CustomUser.objects.create_user(email='other@hrequest.com', password='Pwd!')
        with self.assertRaises(IntegrityError):
            Employee.objects.create(
                user=other_user,
                employee_id_number='EMP-001',
                first_name='Jane',
                last_name='Smith',
                department=self.dept,
                position=self.pos,
                hire_date=datetime.date.today()
            )

    def test_employee_list_view_as_hr_admin(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        response = client.get(reverse('employees:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'EMP-001')

    def test_employee_list_view_denied_for_regular_employee(self):
        client = Client()
        client.login(email='regular_emp@hrequest.com', password='TestPassword2026!')
        response = client.get(reverse('employees:list'))
        # Regular employee has role EMPLOYEE, allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']
        self.assertEqual(response.status_code, 403)

    def test_employee_export_csv_as_hr_admin(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        response = client.get(reverse('employees:export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('EMP-001', response.content.decode('utf-8'))
        self.assertIn('John Doe', response.content.decode('utf-8'))

    def test_onboarding_wizard_access_denied_for_employee(self):
        client = Client()
        client.login(email='regular_emp@hrequest.com', password='TestPassword2026!')
        response = client.get(reverse('employees:onboard_start'))
        self.assertEqual(response.status_code, 403)

    def test_onboarding_wizard_full_flow(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')

        # Step 1
        res1 = client.post(reverse('employees:onboard_step', kwargs={'step': 1}), {
            'first_name': 'Sarah',
            'last_name': 'Connor',
            'birth_date': '1995-05-15',
            'work_location': 'New York',
        })
        self.assertRedirects(res1, reverse('employees:onboard_step', kwargs={'step': 2}))

        # Step 2
        res2 = client.post(reverse('employees:onboard_step', kwargs={'step': 2}), {
            'department': self.dept.id,
            'position': self.pos.id,
            'employment_type': EmploymentType.FULL_TIME,
            'hire_date': '2026-01-10',
        })
        self.assertRedirects(res2, reverse('employees:onboard_step', kwargs={'step': 3}))

        # Step 3
        res3 = client.post(reverse('employees:onboard_step', kwargs={'step': 3}), {
            'work_email': 'sarah.connor@hrequest.com',
            'password': 'TempPassword2026!',
            'role': UserRole.EMPLOYEE,
        })
        self.assertRedirects(res3, reverse('employees:onboard_step', kwargs={'step': 4}))

        # Step 4
        res4 = client.post(reverse('employees:onboard_step', kwargs={'step': 4}), {
            'employee_id_number': 'EMP-099',
            'emergency_contact_name': 'John Connor',
            'emergency_contact_phone': '+1 555-9999',
        })
        self.assertRedirects(res4, reverse('employees:onboard_step', kwargs={'step': 5}))

        # Step 5: Finish & commit
        res5 = client.post(reverse('employees:onboard_step', kwargs={'step': 5}))
        new_emp = Employee.objects.filter(employee_id_number='EMP-099').first()
        self.assertIsNotNone(new_emp)
        self.assertEqual(new_emp.full_name, 'Sarah Connor')
        self.assertEqual(new_emp.user.email, 'sarah.connor@hrequest.com')
        self.assertTrue(new_emp.user.check_password('TempPassword2026!'))
        self.assertRedirects(res5, reverse('employees:detail', kwargs={'pk': new_emp.id}))

    def test_hr_admin_can_terminate_employee(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        res = client.post(reverse('employees:terminate', kwargs={'pk': self.employee.id}))
        self.assertRedirects(res, reverse('employees:list'))
        self.employee.refresh_from_db()
        self.employee.user.refresh_from_db()
        self.assertEqual(self.employee.status, EmployeeStatus.TERMINATED)
        self.assertFalse(self.employee.user.is_active)

    def test_regular_employee_cannot_terminate_or_delete(self):
        client = Client()
        client.login(email='regular_emp@hrequest.com', password='TestPassword2026!')
        res_term = client.post(reverse('employees:terminate', kwargs={'pk': self.employee.id}))
        res_del = client.post(reverse('employees:delete', kwargs={'pk': self.employee.id}))
        self.assertEqual(res_term.status_code, 403)
        self.assertEqual(res_del.status_code, 403)

    def test_hr_admin_can_delete_employee(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        emp_id = self.employee.id
        user_id = self.employee.user_id
        res = client.post(reverse('employees:delete', kwargs={'pk': emp_id}))
        self.assertRedirects(res, reverse('employees:list'))
        self.assertFalse(Employee.objects.filter(id=emp_id).exists())
        self.assertFalse(CustomUser.objects.filter(id=user_id).exists())

    def test_one_time_team_seed_runs_once_and_preserves_deletions(self):
        from django.core.management import call_command
        from apps.attendance.models import Attendance
        from apps.payslips.models import PayslipRecord
        from apps.requests.models import DocumentRequest

        call_command('seed_team_members')
        aux = Employee.objects.filter(user__email='auxtero.rivic@hrequest.com').first()
        self.assertIsNotNone(aux)
        self.assertGreaterEqual(Attendance.objects.filter(employee=aux).count(), 15)
        self.assertEqual(PayslipRecord.objects.filter(employee=aux).count(), 3)
        self.assertEqual(DocumentRequest.objects.filter(employee=aux).count(), 2)
        self.assertFalse(Employee.objects.filter(first_name__icontains='John Anthony').exists())

        # Delete one employee, then re-run seed: should NOT re-create!
        aux.user.delete()
        call_command('seed_team_members')
        self.assertFalse(Employee.objects.filter(user__email='auxtero.rivic@hrequest.com').exists())

    def test_hr_admin_can_edit_employee_profile(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        res = client.post(reverse('employees:edit', kwargs={'pk': self.employee.id}), {
            'employee_id_number': 'HACKED-999',
            'first_name': 'Jonathan',
            'middle_name': 'M',
            'last_name': 'Doe',
            'work_email': 'john.doe@hrequest.com',
            'department': self.dept.id,
            'position': self.pos.id,
            'employment_type': EmploymentType.FULL_TIME,
            'status': EmployeeStatus.ACTIVE,
            'work_location': 'Manila Site',
            'hire_date': '2024-01-01',
            'phone_number': '+63 917 123 4567',
        })
        self.assertRedirects(res, reverse('employees:detail', kwargs={'pk': self.employee.id}))
        self.employee.refresh_from_db()
        self.employee.user.refresh_from_db()
        self.assertEqual(self.employee.employee_id_number, 'EMP-001')
        self.assertEqual(self.employee.first_name, 'Jonathan')
        self.assertEqual(self.employee.work_location, 'Manila Site')
        self.assertEqual(self.employee.user.email, 'john.doe@hrequest.com')

    def test_regular_employee_cannot_edit_employee_profile(self):
        client = Client()
        client.login(email='regular_emp@hrequest.com', password='TestPassword2026!')
        res = client.get(reverse('employees:edit', kwargs={'pk': self.employee.id}))
        self.assertEqual(res.status_code, 403)

