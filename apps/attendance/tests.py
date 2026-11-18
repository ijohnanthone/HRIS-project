import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus
from apps.attendance.models import (
    Attendance,
    AttendanceSource,
    AttendanceStatus,
    ImportBatch,
    ImportBatchStatus,
    ImportRowStatus,
)

class AttendanceEngineTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Operations', code='DEP-OPS')
        self.pos = Position.objects.create(title='Operator', code='POS-OP', department=self.dept)

        self.hr_user = CustomUser.objects.create_user(
            email='hr_admin@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.HR_ADMIN,
            is_staff=True
        )

        self.emp_user = CustomUser.objects.create_user(
            email='emp@hrequest.com',
            password='TestPassword2026!',
            role=UserRole.EMPLOYEE
        )
        self.employee = Employee.objects.create(
            user=self.emp_user,
            employee_id_number='00230',
            first_name='Chris',
            last_name='Glasser',
            department=self.dept,
            position=self.pos,
            hire_date=datetime.date.today()
        )

    def test_web_clock_in_success(self):
        client = Client()
        client.login(email='emp@hrequest.com', password='TestPassword2026!')

        response = client.post(reverse('attendance:clock_in_out'), {'action': 'clock_in'})
        self.assertEqual(response.status_code, 302)

        att = Attendance.objects.filter(employee=self.employee, date=timezone.now().date()).first()
        self.assertIsNotNone(att)
        self.assertIsNotNone(att.clock_in)
        self.assertEqual(att.source, AttendanceSource.WEB)

    def test_web_clock_in_prevent_duplicate(self):
        client = Client()
        client.login(email='emp@hrequest.com', password='TestPassword2026!')

        # First punch in
        client.post(reverse('attendance:clock_in_out'), {'action': 'clock_in'})
        att1 = Attendance.objects.get(employee=self.employee, date=timezone.now().date())
        first_in = att1.clock_in

        # Attempt second punch in on same day
        client.post(reverse('attendance:clock_in_out'), {'action': 'clock_in'})
        att2 = Attendance.objects.get(employee=self.employee, date=timezone.now().date())

        # Should remain the first timestamp
        self.assertEqual(att1.clock_in, att2.clock_in)

    def test_web_clock_out_without_clock_in_fails(self):
        client = Client()
        client.login(email='emp@hrequest.com', password='TestPassword2026!')

        response = client.post(reverse('attendance:clock_in_out'), {'action': 'clock_out'})
        self.assertEqual(response.status_code, 302)

        att = Attendance.objects.filter(employee=self.employee, date=timezone.now().date()).first()
        self.assertIsNone(att.clock_out)

    def test_web_clock_in_and_out_sequence(self):
        client = Client()
        client.login(email='emp@hrequest.com', password='TestPassword2026!')

        client.post(reverse('attendance:clock_in_out'), {'action': 'clock_in'})
        client.post(reverse('attendance:clock_in_out'), {'action': 'clock_out'})

        att = Attendance.objects.get(employee=self.employee, date=timezone.now().date())
        self.assertIsNotNone(att.clock_in)
        self.assertIsNotNone(att.clock_out)

    def test_manual_attendance_correction_by_hr(self):
        att = Attendance.objects.create(
            employee=self.employee,
            date=datetime.date(2026, 11, 1),
            status=AttendanceStatus.ABSENT,
            source=AttendanceSource.WEB
        )

        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')

        response = client.post(reverse('attendance:manual_correction', kwargs={'pk': att.id}), {
            'clock_in': '2026-11-01T08:00',
            'clock_out': '2026-11-01T17:00',
            'status': AttendanceStatus.PRESENT,
            'correction_note': 'Employee forgot badge, verified with team lead.'
        })

        att.refresh_from_db()
        self.assertEqual(att.status, AttendanceStatus.PRESENT)
        self.assertEqual(att.source, AttendanceSource.MANUAL_CORRECTION)
        self.assertTrue(att.is_verified)
        self.assertEqual(att.verified_by, self.hr_user)

    def test_biometric_csv_import_workflow(self):
        csv_data = (
            "employee_id,date,clock_in,clock_out\n"
            "00230,2026-11-15,08:05:00,17:00:00\n"
            "99999,2026-11-15,08:00:00,17:00:00\n"  # Non-existent employee
        )
        csv_file = SimpleUploadedFile("biometric.csv", csv_data.encode('utf-8'), content_type="text/csv")

        client = Client()
        client.login(email='hr_admin@hrequest.com', password='TestPassword2026!')

        # 1. Upload
        upload_res = client.post(reverse('attendance:import_upload'), {'csv_file': csv_file})
        batch = ImportBatch.objects.latest('created_at')
        self.assertRedirects(upload_res, reverse('attendance:import_preview', kwargs={'batch_id': batch.id}))

        # Verify row statuses
        rows = list(batch.rows.order_by('row_number'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].status, ImportRowStatus.VALID)
        self.assertEqual(rows[1].status, ImportRowStatus.INVALID)

        # 2. Confirm import
        confirm_res = client.post(reverse('attendance:import_confirm', kwargs={'batch_id': batch.id}), {'action': 'confirm'})
        self.assertRedirects(confirm_res, reverse('attendance:roster'))

        # Verify Attendance record was created
        att = Attendance.objects.filter(employee=self.employee, date=datetime.date(2026, 11, 15)).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.source, AttendanceSource.BIOMETRIC)
        self.assertEqual(att.status, AttendanceStatus.PRESENT)

    def test_employee_cannot_access_roster_or_import(self):
        client = Client()
        client.login(email='emp@hrequest.com', password='TestPassword2026!')

        res1 = client.get(reverse('attendance:roster'))
        self.assertEqual(res1.status_code, 403)

        res2 = client.get(reverse('attendance:import_upload'))
        self.assertEqual(res2.status_code, 403)
