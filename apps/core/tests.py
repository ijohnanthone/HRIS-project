from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import CustomUser, UserRole
from apps.core.models import Notification, AuditLog

class CoreNotificationTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='testuser@hrequest.local',
            password='Password123!',
            role=UserRole.EMPLOYEE
        )
        self.notif = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='Please complete your timesheet.',
            link='/attendance/my/'
        )

    def test_notification_list_view(self):
        self.client.login(email='testuser@hrequest.local', password='Password123!')
        response = self.client.get(reverse('core:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Notification')

    def test_mark_notification_read(self):
        self.client.login(email='testuser@hrequest.local', password='Password123!')
        response = self.client.get(reverse('core:mark_notification_read', kwargs={'pk': self.notif.id}))
        # Redirects to notification link
        self.assertEqual(response.status_code, 302)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_mark_all_read(self):
        Notification.objects.create(recipient=self.user, title='Second Notif', message='Hello')
        self.client.login(email='testuser@hrequest.local', password='Password123!')
        response = self.client.get(reverse('core:mark_all_notifications_read'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)
