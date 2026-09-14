from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates default event manager and superuser accounts for evaluation.'

    def handle(self, *args, **options):
        # 1. Default Business Event Manager
        manager_user = 'event_manager'
        manager_pass = 'GlobalVox@2026!'
        manager_email = 'events@globalvox.com'

        user, created = User.objects.get_or_create(
            username=manager_user,
            defaults={'email': manager_email, 'first_name': 'GlobalVox', 'last_name': 'Event Manager'}
        )
        user.set_password(manager_pass)
        user.is_staff = False
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created event manager: {manager_user}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated event manager password: {manager_user}"))

        # 2. Admin Superuser
        admin_user = 'admin'
        admin_pass = 'Admin@GlobalVox2026!'
        admin_email = 'admin@globalvox.com'

        admin, admin_created = User.objects.get_or_create(
            username=admin_user,
            defaults={'email': admin_email, 'first_name': 'Admin', 'last_name': 'GlobalVox'}
        )
        admin.set_password(admin_pass)
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        if admin_created:
            self.stdout.write(self.style.SUCCESS(f"Created superuser: {admin_user}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated superuser password: {admin_user}"))
