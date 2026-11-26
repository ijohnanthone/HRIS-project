import datetime
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus, WorkLocation
from apps.attendance.models import Attendance, AttendanceSource, AttendanceStatus
from apps.payslips.models import PayrollPeriod, PayslipRecord, PayslipStatus
from apps.payslips.services.payslip_pdf_generator import generate_payslip_pdf
from apps.requests.models import DocumentRequest, RequestType, RequestStatus, FulfillmentMethod, COETemplate
from apps.requests.services.coe_pdf_generator import generate_coe_pdf
from apps.core.models import AuditLog


SEED_MARKER_ACTION = 'ONE_TIME_TEAM_SEED_V1'


class Command(BaseCommand):
    help = 'One-time seed for the 5 team members (excluding John Anthony) with attendance, payslips, and COE requests.'

    def handle(self, *args, **options):
        if AuditLog.objects.filter(action=SEED_MARKER_ACTION).exists():
            self.stdout.write(self.style.WARNING(
                f"Seed '{SEED_MARKER_ACTION}' has already been executed. Skipping so HR deletions/changes are preserved."
            ))
            return

        # Ensure base departments/positions exist
        exec_dept, _ = Department.objects.get_or_create(
            code='DEP-EXEC',
            defaults={'name': 'Executive Management', 'description': 'Corporate leadership and executive decision making'}
        )
        it_dept, _ = Department.objects.get_or_create(
            code='DEP-IT',
            defaults={'name': 'Information Technology', 'description': 'Software engineering, systems architecture, and IT operations'}
        )
        sales_dept, _ = Department.objects.get_or_create(
            code='DEP-SALES',
            defaults={'name': 'Sales & Marketing', 'description': 'Business development, client relations, and market outreach'}
        )
        fin_dept, _ = Department.objects.get_or_create(
            code='DEP-FIN',
            defaults={'name': 'Finance & Accounting', 'description': 'Financial planning, accounting, and payroll administration'}
        )

        ceo_pos, _ = Position.objects.get_or_create(
            code='POS-CEO',
            defaults={'title': 'Chief Executive Officer', 'department': exec_dept, 'grade_level': 'Exec'}
        )
        java_dev_pos, _ = Position.objects.get_or_create(
            code='POS-DEV-JAVA',
            defaults={'title': 'Java Developer', 'department': it_dept, 'grade_level': 'L3'}
        )
        lead_arch_pos, _ = Position.objects.get_or_create(
            code='POS-ARCH-LEAD',
            defaults={'title': 'Lead Solutions Architect', 'department': it_dept, 'grade_level': 'L5'}
        )
        smm_pos, _ = Position.objects.get_or_create(
            code='POS-MKT-SMM',
            defaults={'title': 'SMM Marketing Manager', 'department': sales_dept, 'grade_level': 'L3'}
        )
        acct_pos, _ = Position.objects.get_or_create(
            code='POS-ACCT-SR',
            defaults={'title': 'Senior Accountant', 'department': fin_dept, 'grade_level': 'L3'}
        )

        hr_user = CustomUser.objects.filter(role=UserRole.HR_ADMIN).first() or CustomUser.objects.filter(is_superuser=True).first()
        active_template = COETemplate.objects.filter(is_active=True).first()

        # Payroll periods (Sep, Oct, Nov 2026)
        periods_data = [
            (9, 2026, 'September 2026', False),
            (10, 2026, 'October 2026', False),
            (11, 2026, 'November 2026', True),
        ]
        payroll_periods = []
        for month, year, label, is_active in periods_data:
            pp, _ = PayrollPeriod.objects.get_or_create(
                period_month=month,
                period_year=year,
                defaults={'label': label, 'is_active': is_active}
            )
            payroll_periods.append(pp)

        team_specs = [
            {
                'email': 'auxtero.rivic@hrequest.com',
                'password': 'hrequest2026',
                'first_name': 'Auxtero',
                'middle_name': '',
                'last_name': 'Rivic',
                'emp_id': '00002',
                'department': it_dept,
                'position': java_dev_pos,
                'work_location': WorkLocation.MANILA,
                'hire_date': datetime.date(2024, 6, 15),
                'salary': Decimal('48500.00'),
                'phone': '+63 917 201 0002',
                'coe_purpose': 'Bank Loan Application',
            },
            {
                'email': 'barzillai.sugian@hrequest.com',
                'password': 'hrequest2026',
                'first_name': 'Barzillai Dave',
                'middle_name': 'Roble',
                'last_name': 'Sugian',
                'emp_id': '00003',
                'department': it_dept,
                'position': lead_arch_pos,
                'work_location': WorkLocation.CEBU,
                'hire_date': datetime.date(2023, 9, 1),
                'salary': Decimal('75000.00'),
                'phone': '+63 917 201 0003',
                'coe_purpose': 'Visa Application',
            },
            {
                'email': 'khalil.veloso@hrequest.com',
                'password': 'hrequest2026',
                'first_name': 'Khalil',
                'middle_name': '',
                'last_name': 'Veloso',
                'emp_id': '00004',
                'department': sales_dept,
                'position': smm_pos,
                'work_location': WorkLocation.HEADQUARTERS,
                'hire_date': datetime.date(2024, 2, 10),
                'salary': Decimal('45000.00'),
                'phone': '+63 917 201 0004',
                'coe_purpose': 'Credit Card Application',
            },
            {
                'email': 'ninoralf.delacruz@hrequest.com',
                'password': 'hrequest2026',
                'first_name': 'Niñoralf',
                'middle_name': '',
                'last_name': 'Dela Cruz',
                'emp_id': '00005',
                'department': exec_dept,
                'position': ceo_pos,
                'work_location': WorkLocation.HEADQUARTERS,
                'hire_date': datetime.date(2022, 1, 5),
                'salary': Decimal('95000.00'),
                'phone': '+63 917 201 0005',
                'coe_purpose': 'International Travel / Visa Requirement',
            },
            {
                'email': 'ronjay.nuguid@hrequest.com',
                'password': 'hrequest2026',
                'first_name': 'Ronjay',
                'middle_name': '',
                'last_name': 'Nuguid',
                'emp_id': '00006',
                'department': fin_dept,
                'position': acct_pos,
                'work_location': WorkLocation.DAVAO,
                'hire_date': datetime.date(2024, 4, 20),
                'salary': Decimal('52000.00'),
                'phone': '+63 917 201 0006',
                'coe_purpose': 'Housing Loan Requirement',
            },
        ]

        tz = timezone.get_current_timezone()
        rng = random.Random(20261126)

        with transaction.atomic():
            ticket_seq = 1001
            for spec in team_specs:
                user, u_created = CustomUser.objects.get_or_create(
                    email=spec['email'],
                    defaults={
                        'role': UserRole.EMPLOYEE,
                        'is_active': True,
                    }
                )
                if u_created:
                    user.set_password(spec['password'])
                    user.save()

                emp_id = spec['emp_id']
                while Employee.objects.filter(employee_id_number=emp_id).exclude(user=user).exists():
                    emp_id = f"{int(emp_id) + 10:05d}"

                emp, _ = Employee.objects.get_or_create(
                    user=user,
                    defaults={
                        'employee_id_number': emp_id,
                        'first_name': spec['first_name'],
                        'middle_name': spec['middle_name'],
                        'last_name': spec['last_name'],
                        'department': spec['department'],
                        'position': spec['position'],
                        'employment_type': EmploymentType.FULL_TIME,
                        'status': EmployeeStatus.ACTIVE,
                        'work_location': spec['work_location'],
                        'hire_date': spec['hire_date'],
                        'phone_number': spec['phone'],
                        'personal_email': spec['email'],
                    }
                )

                # 1. Seed Attendance for all weekdays Nov 2 - Nov 25, 2026 (18 workdays)
                day = datetime.date(2026, 11, 2)
                end_day = datetime.date(2026, 11, 25)
                while day <= end_day:
                    if day.weekday() < 5:  # Mon-Fri
                        in_hour = 8
                        in_min = rng.choice([0, 3, 5, 10, 12, 18, 25])
                        status = AttendanceStatus.LATE if in_min > 15 else AttendanceStatus.PRESENT
                        if rng.random() < 0.12:
                            status = AttendanceStatus.WFH
                        out_hour = 17
                        out_min = rng.choice([0, 5, 12, 20, 30])

                        clock_in = timezone.make_aware(datetime.datetime.combine(day, datetime.time(in_hour, in_min)), tz)
                        clock_out = timezone.make_aware(datetime.datetime.combine(day, datetime.time(out_hour, out_min)), tz)
                        source = AttendanceSource.WEB if status == AttendanceStatus.WFH else rng.choice([AttendanceSource.WEB, AttendanceSource.BIOMETRIC])

                        Attendance.objects.get_or_create(
                            employee=emp,
                            date=day,
                            defaults={
                                'clock_in': clock_in,
                                'clock_out': clock_out,
                                'source': source,
                                'status': status,
                                'is_verified': True,
                                'verified_by': hr_user,
                                'verified_at': clock_out,
                            }
                        )
                    day += datetime.timedelta(days=1)

                # 2. Seed Payslips for Sep, Oct, Nov 2026
                for pp in payroll_periods:
                    if not PayslipRecord.objects.filter(employee=emp, payroll_period=pp).exists():
                        rec = PayslipRecord(
                            employee=emp,
                            payroll_period=pp,
                            total_salary=spec['salary'],
                            status=PayslipStatus.PAID,
                            uploaded_by=hr_user,
                            is_released=True,
                        )
                        pdf_bytes = generate_payslip_pdf(rec)
                        filename = f"Payslip_{emp.employee_id_number}_{pp.label.replace(' ', '_')}.pdf"
                        rec.payslip_file.save(filename, ContentFile(pdf_bytes), save=False)
                        rec.file_size = len(pdf_bytes)
                        rec.save()

                # 3. Seed 1 Approved COE Request & 1 Pending COE Request
                approved_ticket = f"COE-2026-{ticket_seq}"
                ticket_seq += 1
                if not DocumentRequest.objects.filter(ticket_number=approved_ticket).exists():
                    req_app = DocumentRequest.objects.create(
                        ticket_number=approved_ticket,
                        employee=emp,
                        request_type=RequestType.COE_WITH_COMPENSATION,
                        purpose=spec['coe_purpose'],
                        status=RequestStatus.APPROVED,
                        approved_by=hr_user,
                        approved_at=timezone.now(),
                        document_released_at=timezone.now(),
                        fulfillment_method=FulfillmentMethod.AUTO_GENERATED,
                    )
                    coe_bytes = generate_coe_pdf(req_app, active_template)
                    req_app.generated_document.save(f"{approved_ticket}.pdf", ContentFile(coe_bytes), save=True)

                pending_ticket = f"COE-2026-{ticket_seq}"
                ticket_seq += 1
                DocumentRequest.objects.get_or_create(
                    ticket_number=pending_ticket,
                    defaults={
                        'employee': emp,
                        'request_type': RequestType.COE_WITHOUT_COMPENSATION,
                        'purpose': 'Employment Verification',
                        'status': RequestStatus.PENDING,
                    }
                )

                self.stdout.write(self.style.SUCCESS(
                    f"Seeded {emp.full_name} ({emp.employee_id_number}) | Email: {user.email} | Password: {spec['password']}"
                ))

            # Record one-time marker
            AuditLog.objects.create(
                actor=hr_user,
                action=SEED_MARKER_ACTION,
                model_name='Employee',
                object_id='TEAM_SEED_5',
                changes={'details': 'One-time team seed executed for Auxtero Rivic, Barzillai Dave Roble Sugian, Khalil Veloso, Niñoralf Dela Cruz, and Ronjay Nuguid.'}
            )

        self.stdout.write(self.style.SUCCESS("One-time team seed completed successfully!"))
