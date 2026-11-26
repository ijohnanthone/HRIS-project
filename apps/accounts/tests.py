import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserRole

User = get_user_model()

class CustomUserModelTests(TestCase):
    def test_create_regular_user(self):
        user = User.objects.create_user(
            email='testuser@hrequest.com',
            password='Password123!'
        )
        self.assertEqual(user.email, 'testuser@hrequest.com')
        self.assertEqual(user.role, UserRole.EMPLOYEE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertTrue(user.check_password('Password123!'))

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='superadmin@hrequest.com',
            password='AdminPassword123!'
        )
        self.assertEqual(admin.role, UserRole.SUPER_ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_super_admin)

    def test_email_normalization(self):
        user = User.objects.create_user(
            email='MixedCase@hrequest.com',
            password='Password123!'
        )
        self.assertEqual(user.email, 'mixedcase@hrequest.com')

class AuthenticationViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='employee@hrequest.com',
            password='TestPassword2026!'
        )

    def test_login_page_renders_cleanly(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In to HRequest')
        self.assertContains(response, 'Work Email')

    def test_login_successful(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'employee@hrequest.com',
            'password': 'TestPassword2026!',
            'remember_me': True
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_case_insensitive(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'EMPLOYEE@hrequest.com',
            'password': 'TestPassword2026!',
            'remember_me': True
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_invalid_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'employee@hrequest.com',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_dashboard_authenticated(self):
        self.client.login(email='employee@hrequest.com', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertTemplateUsed(response, 'dashboard/employee.html')

    def test_hr_admin_dashboard_routing(self):
        hr_admin = User.objects.create_user(
            email='hr_test@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.HR_ADMIN
        )
        self.client.login(email='hr_test@hrequest.com', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/hr_admin.html')
        self.assertContains(response, 'Total Employees')

    def test_super_admin_dashboard_routing(self):
        super_admin = User.objects.create_superuser(
            email='admin_test@hrequest.com',
            password='TestPassword2026!'
        )
        self.client.login(email='admin_test@hrequest.com', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/super_admin.html')
        self.assertContains(response, 'Control Center')

    def test_hr_staff_dashboard_routing(self):
        hr_staff = User.objects.create_user(
            email='staff_test@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.HR_STAFF
        )
        self.client.login(email='staff_test@hrequest.com', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/hr_staff.html')
        self.assertContains(response, 'HR STAFF OPERATIONS')

    def test_logout_redirects_to_login(self):
        self.client.login(email='employee@hrequest.com', password='TestPassword2026!')
        response = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_employee_can_update_own_contact_info(self):
        import datetime
        from apps.organizations.models import Department, Position
        from apps.employees.models import Employee

        dept = Department.objects.create(name='IT', code='IT-01')
        pos = Position.objects.create(title='Developer', code='DEV-01', department=dept)
        emp = Employee.objects.create(
            user=self.user,
            employee_id_number='EMP-SELF-1',
            first_name='Self',
            last_name='User',
            department=dept,
            position=pos,
            hire_date=datetime.date(2025, 1, 1),
        )
        self.client.login(email='employee@hrequest.com', password='TestPassword2026!')
        res = self.client.post(reverse('accounts:profile'), {
            'phone_number': '+63 917 888 9999',
            'personal_email': 'self.personal@example.com',
            'emergency_contact_name': 'Maria User',
            'emergency_contact_phone': '+63 917 777 6666',
        })
        self.assertRedirects(res, reverse('accounts:profile'))
        emp.refresh_from_db()
        self.assertEqual(emp.phone_number, '+63 917 888 9999')
        self.assertEqual(emp.personal_email, 'self.personal@example.com')
        self.assertEqual(emp.emergency_contact_name, 'Maria User')
        self.assertEqual(emp.emergency_contact_phone, '+63 917 777 6666')

    def test_user_can_change_password(self):
        self.client.login(email='employee@hrequest.com', password='TestPassword2026!')
        res = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'TestPassword2026!',
            'new_password1': 'NewSecurePass2026!',
            'new_password2': 'NewSecurePass2026!',
        })
        self.assertRedirects(res, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass2026!'))

    def test_employee_can_upload_and_remove_avatar_data(self):
        import datetime
        from apps.organizations.models import Department, Position
        from apps.employees.models import Employee

        dept = Department.objects.create(name='HR', code='HR-AV1')
        pos = Position.objects.create(title='Specialist', code='SPEC-AV1', department=dept)
        emp = Employee.objects.create(
            user=self.user,
            employee_id_number='EMP-AV-1',
            first_name='Avatar',
            last_name='Tester',
            department=dept,
            position=pos,
            hire_date=datetime.date(2025, 1, 1),
        )
        self.client.login(email='employee@hrequest.com', password='TestPassword2026!')
        sample_uri = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2w=='
        res = self.client.post(reverse('accounts:profile'), {
            'action': 'avatar',
            'avatar_data': sample_uri,
        })
        self.assertRedirects(res, reverse('accounts:profile'))
        emp.refresh_from_db()
        self.assertEqual(emp.avatar_data, sample_uri)
        self.assertEqual(emp.avatar_url, sample_uri)

        res_rem = self.client.post(reverse('accounts:profile'), {
            'action': 'avatar',
            'avatar_data': 'REMOVE',
        })
        self.assertRedirects(res_rem, reverse('accounts:profile'))
        emp.refresh_from_db()
        self.assertEqual(emp.avatar_data, '')
