"""
Bootstrap a Django superuser from environment variables.

Required:
  DJANGO_SUPERUSER_USERNAME
  DJANGO_SUPERUSER_PASSWORD

Optional:
  DJANGO_SUPERUSER_EMAIL (default: {username}@localhost)
  DJANGO_SUPERUSER_ROLE (default: ADMIN)
  DJANGO_SUPERUSER_FIRST_NAME (default: Admin)
  DJANGO_SUPERUSER_LAST_NAME (default: User)

Usage (from backend/):
  export DJANGO_SUPERUSER_USERNAME=admin
  export DJANGO_SUPERUSER_PASSWORD='strong-temporary-password'
  python create_superuser.py
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.users.models import User


def main() -> int:
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip() or f"{username}@localhost"
    role = os.environ.get("DJANGO_SUPERUSER_ROLE", "ADMIN").strip() or "ADMIN"
    first_name = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "Admin").strip() or "Admin"
    last_name = os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "User").strip() or "User"

    if not username:
        print(
            "Error: DJANGO_SUPERUSER_USERNAME is required.",
            file=sys.stderr,
        )
        return 1

    if not password:
        print(
            "Error: DJANGO_SUPERUSER_PASSWORD is required.",
            file=sys.stderr,
        )
        return 1

    if User.objects.filter(username=username).exists():
        print(f"Superuser '{username}' already exists. Skipping.")
        return 0

    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )

    print(f"Superuser '{user.username}' created successfully.")
    print(f"  Email: {user.email}")
    print(f"  Role: {user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
