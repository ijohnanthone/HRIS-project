from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import CustomUser, UserRole
from apps.organizations.models import Department, Position
from apps.employees.models import Employee, EmployeeStatus
from apps.announcements.models import Announcement, AnnouncementPriority

class AnnouncementTests(TestCase):
    def setUp(self):
        self.hr_user = CustomUser.objects.create_user(
            email='hr_admin@hrequest.com',
            password='Password123!',
            role=UserRole.HR_ADMIN
        )
        self.dept_it = Department.objects.create(name='IT', code='IT')
        self.dept_sales = Department.objects.create(name='Sales', code='SALES')
        self.pos_dev = Position.objects.create(title='Software Engineer', department=self.dept_it)

        self.emp_user = CustomUser.objects.create_user(
            email='employee@hrequest.com',
            password='Password123!',
            role=UserRole.EMPLOYEE
        )
        self.emp_profile = Employee.objects.create(
            user=self.emp_user,
            employee_id_number='00230',
            first_name='Chris',
            last_name='Glasser',
            department=self.dept_it,
            position=self.pos_dev,
            status=EmployeeStatus.ACTIVE,
            hire_date='2024-01-01'
        )

        # Create general announcement
        self.general_announcement = Announcement.objects.create(
            title='General Notice',
            content='This is for all employees.',
            priority=AnnouncementPriority.NORMAL,
            author=self.hr_user
        )

        # Create Sales-only announcement
        self.sales_announcement = Announcement.objects.create(
            title='Sales Only Notice',
            content='This is exclusively for Sales.',
            priority=AnnouncementPriority.HIGH,
            target_department=self.dept_sales,
            author=self.hr_user
        )

    def test_hr_admin_can_view_all_announcements(self):
        self.client.login(email='hr_admin@hrequest.com', password='Password123!')
        response = self.client.get(reverse('announcements:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'General Notice')
        self.assertContains(response, 'Sales Only Notice')

    def test_employee_can_only_view_applicable_announcements(self):
        self.client.login(email='employee@hrequest.com', password='Password123!')
        response = self.client.get(reverse('announcements:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'General Notice')
        # Chris is in IT, so Sales announcement should NOT be in his feed
        self.assertNotContains(response, 'Sales Only Notice')

    def test_hr_admin_can_create_announcement(self):
        self.client.login(email='hr_admin@hrequest.com', password='Password123!')
        response = self.client.post(reverse('announcements:create'), {
            'title': 'New Urgent Policy',
            'content': 'Please review immediately.',
            'priority': AnnouncementPriority.CRITICAL,
            'is_pinned': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Announcement.objects.filter(title='New Urgent Policy').exists())

    def test_employee_cannot_create_announcement(self):
        self.client.login(email='employee@hrequest.com', password='Password123!')
        response = self.client.get(reverse('announcements:create'))
        self.assertEqual(response.status_code, 403)
