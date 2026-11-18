import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus
from apps.payslips.models import PayrollPeriod, PayslipRecord, PayslipStatus
from apps.payslips.forms import PayslipUploadForm

class PayslipManagementTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Finance Dept', code='DEP-FIN2')
        self.pos = Position.objects.create(title='Accountant', code='POS-ACC', department=self.dept)

        self.hr_user = CustomUser.objects.create_user(
            email='hr_admin@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.HR_ADMIN,
            is_staff=True
        )

        self.emp_user1 = CustomUser.objects.create_user(
            email='emp1@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )
        self.emp1 = Employee.objects.create(
            user=self.emp_user1,
            employee_id_number='00401',
            first_name='Kathy',
            last_name='Pacheco',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date(2023, 1, 10)
        )

        self.emp_user2 = CustomUser.objects.create_user(
            email='emp2@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )
        self.emp2 = Employee.objects.create(
            user=self.emp_user2,
            employee_id_number='00402',
            first_name='Eddie',
            last_name='Lake',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date(2023, 2, 10)
        )

        self.period = PayrollPeriod.objects.create(
            label='November 2026',
            period_month=11,
            period_year=2026,
            is_active=True
        )

    def test_payslip_upload_and_duplicate_prevention(self):
        pdf_file1 = SimpleUploadedFile("payslip_1.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        
        # 1. Initial upload
        record1 = PayslipRecord.objects.create(
            employee=self.emp1,
            payroll_period=self.period,
            payslip_file=pdf_file1,
            total_salary=23789.00,
            status=PayslipStatus.PAID,
            uploaded_by=self.hr_user
        )
        self.assertIsNotNone(record1)

        # 2. Attempt duplicate upload via form without replacement flag -> Fails validation
        pdf_file2 = SimpleUploadedFile("payslip_duplicate.pdf", b"%PDF-1.4 duplicate", content_type="application/pdf")
        form = PayslipUploadForm(data={
            'employee': self.emp1.id,
            'payroll_period': self.period.id,
            'total_salary': 25000.00,
            'status': PayslipStatus.PAID,
            'is_replacement': False,
        }, files={'payslip_file': pdf_file2})

        self.assertFalse(form.is_valid())
        self.assertIn("already exists", str(form.errors))

    def test_payslip_replacement_workflow(self):
        pdf_file1 = SimpleUploadedFile("payslip_1.pdf", b"%PDF-1.4 initial content", content_type="application/pdf")
        PayslipRecord.objects.create(
            employee=self.emp1,
            payroll_period=self.period,
            payslip_file=pdf_file1,
            total_salary=20000.00,
            status=PayslipStatus.PAID,
            uploaded_by=self.hr_user
        )

        # Authorized replacement with note
        pdf_file2 = SimpleUploadedFile("payslip_replacement.pdf", b"%PDF-1.4 replaced content", content_type="application/pdf")
        form = PayslipUploadForm(data={
            'employee': self.emp1.id,
            'payroll_period': self.period.id,
            'total_salary': 22500.00,
            'status': PayslipStatus.PAID,
            'is_replacement': True,
            'replacement_note': 'Overtime calculation adjustment authorized by Finance.'
        }, files={'payslip_file': pdf_file2})

        self.assertTrue(form.is_valid())

    def test_guarded_payslip_download(self):
        pdf_file = SimpleUploadedFile("confidential_payslip.pdf", b"%PDF-1.4 test payslip", content_type="application/pdf")
        record = PayslipRecord.objects.create(
            employee=self.emp1,
            payroll_period=self.period,
            payslip_file=pdf_file,
            total_salary=15000.00,
            status=PayslipStatus.PAID,
            is_released=True,
            uploaded_by=self.hr_user
        )

        # 1. Owner employee can download
        client1 = Client()
        client1.login(email='emp1@hrequest.com', password='TestPassword2026!')
        res1 = client1.get(reverse('payslips:download', kwargs={'pk': record.id}))
        self.assertEqual(res1.status_code, 200)

        # 2. Another employee CANNOT download -> 403 Forbidden
        client2 = Client()
        client2.login(email='emp2@hrequest.com', password='TestPassword2026!')
        res2 = client2.get(reverse('payslips:download', kwargs={'pk': record.id}))
        self.assertEqual(res2.status_code, 403)

        # 3. HR Admin can download
        hr_client = Client()
        hr_client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        res3 = hr_client.get(reverse('payslips:download', kwargs={'pk': record.id}))
        self.assertEqual(res3.status_code, 200)

    def test_employee_cannot_access_master_payroll_table(self):
        client = Client()
        client.login(email='emp1@hrequest.com', password='TestPassword2026!')
        res = client.get(reverse('payslips:master_list'))
        self.assertEqual(res.status_code, 403)
