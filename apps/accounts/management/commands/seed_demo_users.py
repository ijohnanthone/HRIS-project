from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser, UserRole

class Command(BaseCommand):
    help = 'Seeds initial demo accounts for Super Admin, HR Admin, HR Staff, and Employee'

    def handle(self, *args, **options):
        password = 'HRequest2026!'
        demo_accounts = [
            {
                'email': 'admin@hrequest.local',
                'role': UserRole.SUPER_ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'label': 'Super Admin'
            },
            {
                'email': 'hr@hrequest.local',
                'role': UserRole.HR_ADMIN,
                'is_staff': True,
                'is_superuser': False,
                'label': 'HR Admin'
            },
            {
                'email': 'staff@hrequest.local',
                'role': UserRole.HR_STAFF,
                'is_staff': True,
                'is_superuser': False,
                'label': 'HR Staff'
            },
            {
                'email': 'employee@hrequest.local',
                'role': UserRole.EMPLOYEE,
                'is_staff': False,
                'is_superuser': False,
                'label': 'Employee'
            },
        ]

        for acc in demo_accounts:
            user, created = CustomUser.objects.get_or_create(
                email=acc['email'],
                defaults={
                    'role': acc['role'],
                    'is_staff': acc['is_staff'],
                    'is_superuser': acc['is_superuser'],
                    'is_active': True,
                }
            )
            user.set_password(password)
            user.role = acc['role']
            user.is_staff = acc['is_staff']
            user.is_superuser = acc['is_superuser']
            user.is_active = True
            user.save()

            status_str = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(
                f"[{status_str}] {acc['label']} -> {acc['email']} / {password}"
            ))

        self.stdout.write(self.style.SUCCESS("\nAll 4 demo user roles successfully seeded!"))
