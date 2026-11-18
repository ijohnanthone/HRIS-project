import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus
from apps.requests.models import (
    DocumentRequest,
    RequestType,
    RequestStatus,
    FulfillmentMethod,
    COETemplate,
    RequestHistory,
)

class COERequestWorkflowTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Legal & HR', code='DEP-LGL')
        self.pos = Position.objects.create(title='Legal Counsel', code='POS-LGL', department=self.dept)

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
            employee_id_number='00301',
            first_name='David',
            last_name='Elson',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date(2023, 1, 15)
        )

        self.emp_user2 = CustomUser.objects.create_user(
            email='emp2@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )
        self.emp2 = Employee.objects.create(
            user=self.emp_user2,
            employee_id_number='00302',
            first_name='Judith',
            last_name='Rodriguez',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date(2023, 3, 10)
        )

        self.template = COETemplate.objects.create(
            name='Default Test COE Template',
            header_title='CERTIFICATE OF EMPLOYMENT',
            signatory_name='Paula Mora',
            signatory_title='HR Manager',
            is_active=True
        )

    def test_employee_submit_coe_request(self):
        client = Client()
        client.login(email='emp1@hrequest.com', password='TestPassword2026!')

        response = client.post(reverse('requests:coe_create'), {
            'request_type': RequestType.COE_WITHOUT_COMPENSATION,
            'purpose': 'Visa Application for Travel',
        })
        self.assertRedirects(response, reverse('requests:my_requests'))

        ticket = DocumentRequest.objects.filter(employee=self.emp1).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.status, RequestStatus.PENDING)
        self.assertTrue(ticket.ticket_number.startswith('COE-'))
        self.assertEqual(ticket.history.count(), 1)
        self.assertEqual(ticket.history.first().action, 'SUBMITTED')

    def test_hr_admin_approve_auto_generates_pdf(self):
        ticket = DocumentRequest.objects.create(
            ticket_number='COE-TEST-001',
            employee=self.emp1,
            request_type=RequestType.COE_WITH_COMPENSATION,
            purpose='Bank Home Loan',
            status=RequestStatus.PENDING
        )

        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')

        response = client.post(reverse('requests:coe_decision', kwargs={'pk': ticket.id}), {
            'decision': 'APPROVE_AUTO'
        })
        self.assertRedirects(response, reverse('requests:coe_detail', kwargs={'pk': ticket.id}))

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, RequestStatus.FULFILLED)
        self.assertEqual(ticket.approved_by, self.hr_user)
        self.assertEqual(ticket.fulfillment_method, FulfillmentMethod.AUTO_GENERATED)
        self.assertTrue(bool(ticket.generated_document))
        self.assertIsNotNone(ticket.document_released_at)

    def test_hr_admin_reject_with_reason(self):
        ticket = DocumentRequest.objects.create(
            ticket_number='COE-TEST-002',
            employee=self.emp1,
            request_type=RequestType.COE_WITHOUT_COMPENSATION,
            purpose='Unverified Purpose',
            status=RequestStatus.PENDING
        )

        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')

        response = client.post(reverse('requests:coe_decision', kwargs={'pk': ticket.id}), {
            'decision': 'REJECT',
            'rejection_reason': 'Employee has pending clearance requirements.'
        })
        self.assertRedirects(response, reverse('requests:coe_detail', kwargs={'pk': ticket.id}))

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, RequestStatus.REJECTED)
        self.assertEqual(ticket.rejection_reason, 'Employee has pending clearance requirements.')

    def test_guarded_coe_download(self):
        ticket = DocumentRequest.objects.create(
            ticket_number='COE-TEST-003',
            employee=self.emp1,
            request_type=RequestType.COE_WITHOUT_COMPENSATION,
            purpose='Apartment Lease',
            status=RequestStatus.PENDING
        )

        client = Client()
        client.login(email='emp1@hrequest.com', password='TestPassword2026!')

        # 1. Attempt download before approval -> Denied
        res1 = client.get(reverse('requests:coe_download', kwargs={'pk': ticket.id}))
        self.assertEqual(res1.status_code, 403)

        # 2. HR approves and generates PDF
        hr_client = Client()
        hr_client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')
        hr_client.post(reverse('requests:coe_decision', kwargs={'pk': ticket.id}), {
            'decision': 'APPROVE_AUTO'
        })

        # 3. Requesting employee can now download
        res2 = client.get(reverse('requests:coe_download', kwargs={'pk': ticket.id}))
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2['Content-Type'], 'application/pdf')

        # 4. Another employee CANNOT download this certificate
        client2 = Client()
        client2.login(email='emp2@hrequest.com', password='TestPassword2026!')
        res3 = client2.get(reverse('requests:coe_download', kwargs={'pk': ticket.id}))
        self.assertEqual(res3.status_code, 403)

    def test_employee_cannot_access_hr_coe_queue(self):
        client = Client()
        client.login(email='emp1@hrequest.com', password='TestPassword2026!')
        response = client.get(reverse('requests:coe_list'))
        self.assertEqual(response.status_code, 403)
