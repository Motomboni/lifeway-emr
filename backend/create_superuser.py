"""
Script to create a superuser for the EMR system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User

# Create superuser
username = 'Damiano'
email = 'damiano@emr.local'
password = 'Von@@@&&&1968'

if User.objects.filter(username=username).exists():
    print(f"User '{username}' already exists. Updating password...")
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.role = 'DOCTOR'
    user.first_name = 'Damiano'
    user.last_name = 'Admin'
    user.save()
    print(f"User '{username}' updated successfully!")
else:
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name='Damiano',
        last_name='Admin',
        role='DOCTOR'
    )
    print(f"Superuser '{username}' created successfully!")

print(f"\nLogin credentials:")
print(f"  Username: {username}")
print(f"  Password: {password}")
print(f"  Role: {user.role}")
print(f"  Is Superuser: {user.is_superuser}")
