import os
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus
from apps.documents.models import EmployeeDocument, DocumentCategory

class DocumentVaultSecurityTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Technology', code='DEP-TECH')
        self.pos = Position.objects.create(title='Developer', code='POS-DEV', department=self.dept)

        self.hr_admin = CustomUser.objects.create_user(
            email='hr_admin@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.HR_ADMIN,
            is_staff=True
        )

        self.employee_user1 = CustomUser.objects.create_user(
            email='emp1@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )
        self.emp1 = Employee.objects.create(
            user=self.employee_user1,
            employee_id_number='EMP-001',
            first_name='John',
            last_name='Doe',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date.today()
        )

        self.employee_user2 = CustomUser.objects.create_user(
            email='emp2@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )
        self.emp2 = Employee.objects.create(
            user=self.employee_user2,
            employee_id_number='EMP-002',
            first_name='Jane',
            last_name='Smith',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date.today()
        )

        # Standard (non-confidential) document for emp1
        self.public_doc = EmployeeDocument.objects.create(
            employee=self.emp1,
            title='Government ID',
            category=DocumentCategory.GOVERNMENT_ID,
            file=SimpleUploadedFile("id_card.pdf", b"%PDF-1.4 test id file content"),
            is_confidential=False,
            uploaded_by=self.hr_admin
        )

        # Confidential document for emp1
        self.confidential_doc = EmployeeDocument.objects.create(
            employee=self.emp1,
            title='Contract & Salary Addendum',
            category=DocumentCategory.CONTRACT,
            file=SimpleUploadedFile("contract.pdf", b"%PDF-1.4 test contract content"),
            is_confidential=True,
            uploaded_by=self.hr_admin
        )

    def test_hr_admin_can_download_confidential_and_standard_docs(self):
        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')

        # Download standard doc
        res1 = client.get(reverse('documents:secure_download', kwargs={'pk': self.public_doc.id}))
        self.assertEqual(res1.status_code, 200)

        # Download confidential doc
        res2 = client.get(reverse('documents:secure_download', kwargs={'pk': self.confidential_doc.id}))
        self.assertEqual(res2.status_code, 200)

    def test_employee_can_download_own_standard_doc(self):
        client = Client()
        client.login(email='emp1@hrequest.com', password='TestPassword2026!')
        res = client.get(reverse('documents:secure_download', kwargs={'pk': self.public_doc.id}))
        self.assertEqual(res.status_code, 200)

    def test_employee_cannot_download_own_confidential_doc(self):
        client = Client()
        client.login(email='emp1@hrequest.com', password='TestPassword2026!')
        res = client.get(reverse('documents:secure_download', kwargs={'pk': self.confidential_doc.id}))
        # Confidental docs are restricted from employee self-download
        self.assertEqual(res.status_code, 403)

    def test_employee_cannot_download_other_employee_doc(self):
        client = Client()
        client.login(email='emp2@hrequest.com', password='TestPassword2026!')
        res = client.get(reverse('documents:secure_download', kwargs={'pk': self.public_doc.id}))
        # Emp2 cannot access Emp1's documents
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_download_redirects(self):
        client = Client()
        res = client.get(reverse('documents:secure_download', kwargs={'pk': self.public_doc.id}))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.url.startswith(reverse('accounts:login')))
