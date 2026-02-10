"""
Custom createsuperuser command that handles the role field.

This command extends Django's createsuperuser to prompt for the role field
which is required in the EMR system.
"""
from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction


class Command(BaseCommand):
    """Custom createsuperuser command with role field support."""
    
    def add_arguments(self, parser):
        """Add role argument to the command."""
        super().add_arguments(parser)
        parser.add_argument(
            '--role',
            type=str,
            dest='role',
            default=None,
            metavar='ROLE',
            help='User role (ADMIN, DOCTOR, NURSE, RECEPTIONIST, etc.). Defaults to ADMIN for superuser.',
        )
    
    def handle(self, *args, **options):
        """Handle the createsuperuser command with role support."""
        username = options.get('username')
        email = options.get('email')
        role = options.get('role')
        database = options.get('database', 'default')
        
        UserModel = self.get_user_model()
        
        # If role is not provided via command line, prompt for it (default to ADMIN for superuser)
        if not role:
            try:
                role = self._get_role_interactive()
            except (EOFError, KeyboardInterrupt):
                # If interactive input fails, default to ADMIN
                role = 'ADMIN'
        
        # Default to ADMIN if still not set
        if not role or role.strip() == '':
            role = 'ADMIN'
        
        # Validate role
        valid_roles = [choice[0] for choice in UserModel.ROLE_CHOICES]
        if role not in valid_roles:
            raise ValidationError(
                f"Invalid role: {role}. Valid roles are: {', '.join(valid_roles)}"
            )
        
        # Get username, email, password from parent command
        # We'll override the user creation to include role
        username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
        
        # Get username
        if not username:
            try:
                username = self._get_input_data(
                    username_field,
                    'Username',
                    username
                )
            except (EOFError, KeyboardInterrupt):
                raise ValidationError("Username is required.")
        
        # Get email
        email_field = UserModel._meta.get_field('email')
        if not email:
            try:
                email = self._get_input_data(
                    email_field,
                    'Email address',
                    email
                )
            except (EOFError, KeyboardInterrupt):
                email = None  # Email is optional
        
        # Get password
        try:
            password = self._get_password()
        except (EOFError, KeyboardInterrupt):
            raise ValidationError("Password is required.")
        
        # Create the superuser with role
        try:
            with transaction.atomic(using=database):
                # Use the manager's create_superuser method which handles role
                user = UserModel.objects.db_manager(database).create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    role=role
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Superuser "{username}" created successfully with role "{role}".'
                    )
                )
        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {str(e)}"))
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise ValidationError(f"Error creating superuser: {str(e)}")
    
    def _get_role_interactive(self):
        """Prompt user for role in interactive mode."""
        UserModel = self.get_user_model()
        valid_roles = [choice[0] for choice in UserModel.ROLE_CHOICES]
        role_display = '\n'.join([f'  {i+1}. {choice[1]} ({choice[0]})' 
                                  for i, choice in enumerate(UserModel.ROLE_CHOICES)])
        
        while True:
            self.stdout.write('\nAvailable roles:')
            self.stdout.write(role_display)
            role_input = input('\nRole (default: ADMIN): ').strip().upper()
            
            if not role_input:
                return 'ADMIN'  # Default to ADMIN for superuser
            
            # Try to match by role code
            if role_input in valid_roles:
                return role_input
            
            # Try to match by number
            try:
                role_index = int(role_input) - 1
                if 0 <= role_index < len(valid_roles):
                    return valid_roles[role_index]
            except ValueError:
                pass
            
            # Try partial match
            matching_roles = [r for r in valid_roles if r.startswith(role_input)]
            if len(matching_roles) == 1:
                return matching_roles[0]
            
            self.stdout.write(self.style.ERROR(
                f'Invalid role: {role_input}. Please choose from the list above.'
            ))
    
    def _get_input_data(self, field, message, default=None):
        """Get input data for a field."""
        raw_value = input(f'{message}: ')
        if default and not raw_value:
            return default
        return raw_value
    
    def _get_password(self):
        """Get password from user input."""
        from getpass import getpass
        
        password = getpass('Password: ')
        password_again = getpass('Password (again): ')
        
        if password != password_again:
            raise ValidationError("Passwords don't match.")
        
        if not password:
            raise ValidationError("Password cannot be blank.")
        
        return password

