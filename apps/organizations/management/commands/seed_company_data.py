import datetime
from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmploymentType, EmployeeStatus

class Command(BaseCommand):
    help = 'Seeds realistic organizational structure, departments, positions, and employee records matching UI reference'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Departments & Positions...")

        # 1. Departments
        exec_dept, _ = Department.objects.get_or_create(
            code='DEP-EXEC',
            defaults={'name': 'Executive Management', 'description': 'Corporate leadership and executive decision making'}
        )
        hr_dept, _ = Department.objects.get_or_create(
            code='DEP-HR',
            defaults={'name': 'Human Resources', 'description': 'People operations, recruitment, and organizational culture'}
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

        # 2. Positions
        ceo_pos, _ = Position.objects.get_or_create(
            code='POS-CEO',
            defaults={'title': 'Chief Executive Officer', 'department': exec_dept, 'grade_level': 'Exec'}
        )
        hr_mgr_pos, _ = Position.objects.get_or_create(
            code='POS-HR-MGR',
            defaults={'title': 'HR Manager', 'department': hr_dept, 'grade_level': 'L4'}
        )
        hr_spec_pos, _ = Position.objects.get_or_create(
            code='POS-HR-SPEC',
            defaults={'title': 'HR Operations Specialist', 'department': hr_dept, 'grade_level': 'L2'}
        )
        java_dev_pos, _ = Position.objects.get_or_create(
            code='POS-DEV-JAVA',
            defaults={'title': 'Java Developer', 'department': it_dept, 'grade_level': 'L3'}
        )
        sr_dev_pos, _ = Position.objects.get_or_create(
            code='POS-DEV-SR',
            defaults={'title': 'Senior Full Stack Developer', 'department': it_dept, 'grade_level': 'L4'}
        )
        lead_arch_pos, _ = Position.objects.get_or_create(
            code='POS-ARCH-LEAD',
            defaults={'title': 'Lead Solutions Architect', 'department': it_dept, 'grade_level': 'L5'}
        )
        sales_head_pos, _ = Position.objects.get_or_create(
            code='POS-SALES-HEAD',
            defaults={'title': 'Head of Sales', 'department': sales_dept, 'grade_level': 'L4'}
        )
        sales_rep_pos, _ = Position.objects.get_or_create(
            code='POS-SALES-REP',
            defaults={'title': 'Sales Representative', 'department': sales_dept, 'grade_level': 'L2'}
        )
        smm_pos, _ = Position.objects.get_or_create(
            code='POS-MKT-SMM',
            defaults={'title': 'SMM Marketing Manager', 'department': sales_dept, 'grade_level': 'L3'}
        )
        acct_pos, _ = Position.objects.get_or_create(
            code='POS-ACCT-SR',
            defaults={'title': 'Senior Accountant', 'department': fin_dept, 'grade_level': 'L3'}
        )

        self.stdout.write("Setting up HR Admin profile (hr@hrequest.com)...")

        # Paula Mora (HR Admin)
        hr_user, created = CustomUser.objects.get_or_create(
            email='hr@hrequest.com',
            defaults={
                'role': UserRole.HR_ADMIN,
                'is_staff': True,
                'is_superuser': False,
                'is_active': True,
            }
        )
        if created:
            hr_user.set_password('hrrequest')
            hr_user.save()

        paula, _ = Employee.objects.get_or_create(
            user=hr_user,
            defaults={
                'employee_id_number': '00105',
                'first_name': 'Paula',
                'last_name': 'Mora',
                'department': hr_dept,
                'position': hr_mgr_pos,
                'employment_type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'work_location': 'Headquarters',
                'hire_date': datetime.date(2022, 3, 1),
                'phone_number': '+63 917 000 0001',
                'personal_email': 'hr@hrequest.com',
            }
        )
        hr_dept.head_of_department = paula
        hr_dept.save()

        # Seed default active COE Template
        from apps.requests.models import COETemplate, TemplateType
        COETemplate.objects.get_or_create(
            name='Standard Corporate COE Template v2026',
            defaults={
                'template_type': TemplateType.WITHOUT_COMPENSATION,
                'header_title': 'CERTIFICATE OF EMPLOYMENT',
                'signatory_name': 'Paula Mora',
                'signatory_title': 'Human Resources Manager',
                'is_active': True,
                'uploaded_by': hr_user,
            }
        )

        # Seed current Payroll Period
        from apps.payslips.models import PayrollPeriod
        PayrollPeriod.objects.get_or_create(
            period_month=11,
            period_year=2026,
            defaults={'label': 'November 2026', 'is_active': True}
        )

        # Seed Announcements
        from apps.announcements.models import Announcement, AnnouncementPriority
        from apps.core.models import AuditLog

        Announcement.objects.get_or_create(
            title="Welcome to HRequest HRIS",
            defaults={
                'content': "Welcome to HRequest! HR Administrators can onboard new employees, manage attendance, issue COEs, and upload payroll slips.",
                'priority': AnnouncementPriority.HIGH,
                'is_pinned': True,
                'is_published': True,
                'author': hr_user,
            }
        )

        # Seed initial Audit Log
        AuditLog.objects.get_or_create(
            action="SYSTEM_INIT",
            model_name="System",
            object_id="0",
            defaults={
                'actor': hr_user,
                'changes': {'event': 'Initial seeding of HRequest HRIS HR-only master setup'},
                'ip_address': '127.0.0.1'
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {Department.objects.count()} departments, "
            f"{Position.objects.count()} positions, and HR Admin account (hr@hrequest.com)!"
        ))
