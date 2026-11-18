from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmployeeStatus, EmploymentType

class ReportsAndSystemAdminTests(TestCase):
    def setUp(self):
        self.super_admin = CustomUser.objects.create_superuser(
            email='admin@hrequest.com',
            password='Password123!'
        )
        self.hr_admin = CustomUser.objects.create_user(
            email='hr@hrequest.com',
            password='Password123!',
            role=UserRole.HR_ADMIN
        )
        self.employee = CustomUser.objects.create_user(
            email='employee@hrequest.com',
            password='Password123!',
            role=UserRole.EMPLOYEE
        )

        self.dept = Department.objects.create(name='Technology', code='TECH')
        self.pos = Position.objects.create(title='Software Engineer', department=self.dept)
        self.emp_profile = Employee.objects.create(
            user=self.employee,
            employee_id_number='00999',
            first_name='John',
            last_name='Doe',
            department=self.dept,
            position=self.pos,
            status=EmployeeStatus.ACTIVE,
            hire_date='2024-01-01'
        )

    # --- Reports Tests ---
    def test_reports_accessible_to_hr_admin(self):
        self.client.login(email='hr@hrequest.com', password='Password123!')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Workforce Intelligence')
        self.assertContains(response, 'Technology')

    def test_reports_forbidden_to_regular_employee(self):
        self.client.login(email='employee@hrequest.com', password='Password123!')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_export_workforce_csv(self):
        self.client.login(email='hr@hrequest.com', password='Password123!')
        response = self.client.get(reverse('reports:export_workforce'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, '00999')
        self.assertContains(response, 'John Doe')

    # --- System Admin Portal Tests ---
    def test_system_admin_portal_accessible_to_super_admin(self):
        self.client.login(email='admin@hrequest.com', password='Password123!')
        response = self.client.get(reverse('system_admin:portal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System Administration Portal')
        self.assertContains(response, 'Total System Accounts')

    def test_system_admin_portal_forbidden_to_hr_admin(self):
        self.client.login(email='hr@hrequest.com', password='Password123!')
        response = self.client.get(reverse('system_admin:portal'))
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_create_user(self):
        self.client.login(email='admin@hrequest.com', password='Password123!')
        response = self.client.post(reverse('system_admin:user_create'), {
            'email': 'new_staff@hrequest.com',
            'role': UserRole.HR_STAFF,
            'password': 'TempPassword2026!',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='new_staff@hrequest.com', role=UserRole.HR_STAFF).exists())

    def test_super_admin_can_update_role(self):
        self.client.login(email='admin@hrequest.com', password='Password123!')
        target_user = CustomUser.objects.create_user(
            email='promote_me@hrequest.com',
            password='Password123!',
            role=UserRole.EMPLOYEE
        )
        response = self.client.post(reverse('system_admin:user_update_role', kwargs={'pk': target_user.id}), {
            'role': UserRole.HR_ADMIN
        })
        self.assertEqual(response.status_code, 302)
        target_user.refresh_from_db()
        self.assertEqual(target_user.role, UserRole.HR_ADMIN)

    def test_super_admin_can_toggle_user_status(self):
        self.client.login(email='admin@hrequest.com', password='Password123!')
        target_user = CustomUser.objects.create_user(
            email='deactivate_me@hrequest.com',
            password='Password123!',
            role=UserRole.EMPLOYEE
        )
        self.assertTrue(target_user.is_active)
        response = self.client.post(reverse('system_admin:user_toggle_status', kwargs={'pk': target_user.id}))
        self.assertEqual(response.status_code, 302)
        target_user.refresh_from_db()
        self.assertFalse(target_user.is_active)

    def test_super_admin_can_reset_password(self):
        self.client.login(email='admin@hrequest.com', password='Password123!')
        target_user = CustomUser.objects.create_user(
            email='reset_pwd@hrequest.com',
            password='OldPassword123!',
            role=UserRole.EMPLOYEE
        )
        response = self.client.post(reverse('system_admin:user_reset_password', kwargs={'pk': target_user.id}), {
            'new_password': 'BrandNewPassword2026!'
        })
        self.assertEqual(response.status_code, 302)
        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password('BrandNewPassword2026!'))
