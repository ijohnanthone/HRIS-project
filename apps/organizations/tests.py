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
            email='test@hrequest.local',
            password='TestPassword2026!'
        )
        client = Client()
        client.login(email='test@hrequest.local', password='TestPassword2026!')
        response = client.get(reverse('organizations:company_structure'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Company Structure')
        self.assertContains(response, 'Engineering')
