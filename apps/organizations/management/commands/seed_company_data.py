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

        self.stdout.write("Linking core demo accounts to Employee profiles...")
        default_pwd = 'HRequest2026!'

        # 3. Core Accounts -> Employee Links
        # Kurt Bates (Super Admin)
        admin_user = CustomUser.objects.get(email='admin@hrequest.local')
        kurt, _ = Employee.objects.get_or_create(
            user=admin_user,
            defaults={
                'employee_id_number': '00100',
                'first_name': 'Kurt',
                'last_name': 'Bates',
                'department': exec_dept,
                'position': ceo_pos,
                'employment_type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'work_location': 'Headquarters, New York',
                'hire_date': datetime.date(2021, 1, 15),
                'phone_number': '+1 (555) 019-2831',
                'personal_email': 'kurt.bates@example.com',
            }
        )
        exec_dept.head_of_department = kurt
        exec_dept.save()

        # Paula Mora (HR Admin - matching UI Reference)
        hr_user = CustomUser.objects.get(email='hr@hrequest.local')
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
                'work_location': 'New York',
                'hire_date': datetime.date(2022, 3, 1),
                'phone_number': '+1 (555) 014-9982',
                'personal_email': 'paula.mora@example.com',
            }
        )
        hr_dept.head_of_department = paula
        hr_dept.save()

        # Alex Buckmaster (HR Staff)
        staff_user = CustomUser.objects.get(email='staff@hrequest.local')
        Employee.objects.get_or_create(
            user=staff_user,
            defaults={
                'employee_id_number': '00112',
                'first_name': 'Alex',
                'last_name': 'Buckmaster',
                'department': hr_dept,
                'position': hr_spec_pos,
                'employment_type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'work_location': 'New York',
                'hire_date': datetime.date(2023, 6, 15),
                'phone_number': '+1 (555) 018-7741',
                'personal_email': 'alex.b@example.com',
            }
        )

        # Chris Glasser (Employee - Java Developer, matching UI reference onboarding screen)
        emp_user = CustomUser.objects.get(email='employee@hrequest.local')
        Employee.objects.get_or_create(
            user=emp_user,
            defaults={
                'employee_id_number': '00230',
                'first_name': 'Chris',
                'last_name': 'Glasser',
                'department': it_dept,
                'position': java_dev_pos,
                'employment_type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'work_location': 'New York',
                'hire_date': datetime.date(2023, 7, 12),
                'phone_number': '+1 (555) 019-3382',
                'personal_email': 'chris.glasser@example.com',
            }
        )

        # 4. Additional Sample Employees (Directly from reference table screen 2)
        additional_samples = [
            {
                'email': 'kathy.pacheco@hrequest.local',
                'id_num': '00236',
                'first_name': 'Kathy',
                'last_name': 'Pacheco',
                'dept': sales_dept,
                'pos': sales_rep_pos,
                'type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'loc': 'New York',
                'phone': '+1 (555) 651-0921',
                'hire': datetime.date(2023, 1, 10),
            },
            {
                'email': 'frances.swann@hrequest.local',
                'id_num': '00235',
                'first_name': 'Frances',
                'last_name': 'Swann',
                'dept': fin_dept,
                'pos': acct_pos,
                'type': EmploymentType.PART_TIME,
                'status': EmployeeStatus.OFFER_PENDING,
                'loc': 'Singapore',
                'phone': '+65 744-6291',
                'hire': datetime.date(2024, 2, 1),
            },
            {
                'email': 'eddie.lake@hrequest.local',
                'id_num': '00234',
                'first_name': 'Eddie',
                'last_name': 'Lake',
                'dept': it_dept,
                'pos': sr_dev_pos,
                'type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ONBOARDING,
                'loc': 'London',
                'phone': '+44 267 739-6240',
                'hire': datetime.date(2024, 4, 15),
            },
            {
                'email': 'judith.rodriguez@hrequest.local',
                'id_num': '00233',
                'first_name': 'Judith',
                'last_name': 'Rodriguez',
                'dept': it_dept,
                'pos': lead_arch_pos,
                'type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'loc': 'Singapore',
                'phone': '+65 474-9169',
                'hire': datetime.date(2022, 8, 20),
            },
            {
                'email': 'john.dukes@hrequest.local',
                'id_num': '00232',
                'first_name': 'John',
                'last_name': 'Dukes',
                'dept': sales_dept,
                'pos': smm_pos,
                'type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'loc': 'New York',
                'phone': '+1 (555) 838-9011',
                'hire': datetime.date(2023, 3, 5),
            },
            {
                'email': 'autumn.phillips@hrequest.local',
                'id_num': '00231',
                'first_name': 'Autumn',
                'last_name': 'Phillips',
                'dept': sales_dept,
                'pos': sales_head_pos,
                'type': EmploymentType.FULL_TIME,
                'status': EmployeeStatus.ACTIVE,
                'loc': 'London',
                'phone': '+44 765 322-1399',
                'hire': datetime.date(2022, 5, 18),
            },
        ]

        for s in additional_samples:
            user, _ = CustomUser.objects.get_or_create(
                email=s['email'],
                defaults={
                    'role': UserRole.EMPLOYEE,
                    'is_staff': False,
                    'is_superuser': False,
                    'is_active': True,
                }
            )
            user.set_password(default_pwd)
            user.save()

            Employee.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id_number': s['id_num'],
                    'first_name': s['first_name'],
                    'last_name': s['last_name'],
                    'department': s['dept'],
                    'position': s['pos'],
                    'employment_type': s['type'],
                    'status': s['status'],
                    'work_location': s['loc'],
                    'hire_date': s['hire'],
                    'phone_number': s['phone'],
                }
            )

        # Set sales dept head
        autumn = Employee.objects.filter(first_name='Autumn', last_name='Phillips').first()
        if autumn:
            sales_dept.head_of_department = autumn
            sales_dept.save()

        # Set IT dept head
        judith = Employee.objects.filter(first_name='Judith', last_name='Rodriguez').first()
        if judith:
            it_dept.head_of_department = judith
            it_dept.save()

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {Department.objects.count()} departments, "
            f"{Position.objects.count()} positions, and {Employee.objects.count()} employee records!"
        ))
