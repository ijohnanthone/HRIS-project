import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserRole

User = get_user_model()

class CustomUserModelTests(TestCase):
    def test_create_regular_user(self):
        user = User.objects.create_user(
            email='testuser@hrequest.local',
            password='Password123!'
        )
        self.assertEqual(user.email, 'testuser@hrequest.local')
        self.assertEqual(user.role, UserRole.EMPLOYEE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertTrue(user.check_password('Password123!'))

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='superadmin@hrequest.local',
            password='AdminPassword123!'
        )
        self.assertEqual(admin.role, UserRole.SUPER_ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_super_admin)

    def test_email_normalization(self):
        user = User.objects.create_user(
            email='MixedCase@HREQUEST.Local',
            password='Password123!'
        )
        self.assertEqual(user.email, 'mixedcase@hrequest.local')

class AuthenticationViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='employee@hrequest.local',
            password='TestPassword2026!'
        )

    def test_login_page_renders_cleanly(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In to HRequest')
        self.assertContains(response, 'Work Email')

    def test_login_successful(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'employee@hrequest.local',
            'password': 'TestPassword2026!',
            'remember_me': True
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_case_insensitive(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'EMPLOYEE@HREQUEST.LOCAL',
            'password': 'TestPassword2026!',
            'remember_me': True
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_invalid_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'employee@hrequest.local',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_dashboard_authenticated(self):
        self.client.login(email='employee@hrequest.local', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertTemplateUsed(response, 'dashboard/employee.html')

    def test_hr_admin_dashboard_routing(self):
        hr_admin = User.objects.create_user(
            email='hr_test@hrequest.local',
            password='TestPassword2026!',
            role=UserRole.HR_ADMIN
        )
        self.client.login(email='hr_test@hrequest.local', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/hr_admin.html')
        self.assertContains(response, 'Total Employees')

    def test_super_admin_dashboard_routing(self):
        super_admin = User.objects.create_superuser(
            email='admin_test@hrequest.local',
            password='TestPassword2026!'
        )
        self.client.login(email='admin_test@hrequest.local', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/super_admin.html')
        self.assertContains(response, 'Control Center')

    def test_hr_staff_dashboard_routing(self):
        hr_staff = User.objects.create_user(
            email='staff_test@hrequest.local',
            password='TestPassword2026!',
            role=UserRole.HR_STAFF
        )
        self.client.login(email='staff_test@hrequest.local', password='TestPassword2026!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/hr_staff.html')
        self.assertContains(response, 'HR STAFF OPERATIONS')

    def test_logout_redirects_to_login(self):
        self.client.login(email='employee@hrequest.local', password='TestPassword2026!')
        response = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
