from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser, UserRole


class Command(BaseCommand):
    help = 'Seeds the primary HR Admin account (hr@hrequest.com / hrrequest) and removes old demo accounts.'

    def handle(self, *args, **options):
        password = 'hrrequest'

        # Remove old multi-role demo accounts if they exist
        old_demo_emails = [
            'admin@hrequest.com',
            'staff@hrequest.com',
            'employee@hrequest.com',
        ]
        deleted_count, _ = CustomUser.objects.filter(email__in=old_demo_emails).delete()
        if deleted_count:
            self.stdout.write(self.style.WARNING(f"Removed {deleted_count} old demo account record(s)."))

        hr_user, created = CustomUser.objects.get_or_create(
            email='hr@hrequest.com',
            defaults={
                'role': UserRole.HR_ADMIN,
                'is_staff': True,
                'is_superuser': False,
                'is_active': True,
            }
        )
        hr_user.set_password(password)
        hr_user.role = UserRole.HR_ADMIN
        hr_user.is_staff = True
        hr_user.is_superuser = False
        hr_user.is_active = True
        hr_user.save()

        status_str = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"[{status_str}] HR Admin -> hr@hrequest.com / {password}"
        ))
