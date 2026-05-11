"""
Create or update a superuser for local/staging setup.

Required environment variable:
    DJANGO_SUPERUSER_PASSWORD

Optional environment variables:
    DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL,
    DJANGO_SUPERUSER_FIRST_NAME, DJANGO_SUPERUSER_LAST_NAME,
    DJANGO_SUPERUSER_ROLE
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'Damiano')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'damiano@emr.local')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Damiano')
last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'Admin')
role = os.environ.get('DJANGO_SUPERUSER_ROLE', 'ADMIN')

if not password:
    raise SystemExit(
        "DJANGO_SUPERUSER_PASSWORD is required. "
        "Set it in the shell before running this script."
    )

if User.objects.filter(username=username).exists():
    print(f"User '{username}' already exists. Updating password...")
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.role = role
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.save()
    print(f"User '{username}' updated successfully!")
else:
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role
    )
    print(f"Superuser '{username}' created successfully!")

print(f"\nLogin credentials:")
print(f"  Username: {username}")
print(f"  Role: {user.role}")
print(f"  Is Superuser: {user.is_superuser}")
