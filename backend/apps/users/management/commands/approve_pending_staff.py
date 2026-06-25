"""
Activate staff accounts that are waiting for admin approval (is_active=False).
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Activate pending staff accounts so they can sign in.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            help='Activate a single user by username',
        )
        parser.add_argument(
            '--unlock',
            action='store_true',
            help='Also clear lockout counters (failed_login_attempts, locked_until)',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        unlock = options.get('unlock')

        qs = User.objects.filter(is_active=False).exclude(role='PATIENT')
        if username:
            qs = qs.filter(username=username)

        count = 0
        for user in qs:
            user.is_active = True
            update_fields = ['is_active']
            if unlock:
                user.failed_login_attempts = 0
                user.locked_until = None
                update_fields.extend(['failed_login_attempts', 'locked_until'])
            user.save(update_fields=update_fields)
            count += 1
            self.stdout.write(self.style.SUCCESS(f'Activated {user.username} ({user.role})'))

        if count == 0:
            self.stdout.write('No pending staff accounts found.')
        else:
            self.stdout.write(self.style.SUCCESS(f'Activated {count} account(s).'))
