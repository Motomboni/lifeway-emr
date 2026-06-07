"""
Helper script to load environment variables from .env file.

This script can be imported in settings.py to load .env variables.
Alternatively, you can use python-decouple or django-environ packages.
"""

import os
from pathlib import Path


def load_env_file(env_file=".env"):
    """
    Load environment variables from .env file.

    This is a simple implementation. For production, consider using:
    - python-decouple
    - django-environ
    - python-dotenv

    Looks for .env in:
    1. backend/.env (same directory as this file)
    2. ../.env (project root, parent of backend directory)
    """
    # First try backend/.env (Django standard)
    backend_env = Path(__file__).resolve().parent / env_file
    # Then try project root/.env (current setup)
    root_env = Path(__file__).resolve().parent.parent / env_file

    paths = []
    if root_env.exists():
        paths.append(root_env)
    if backend_env.exists():
        paths.append(backend_env)
    if not paths:
        return

    for env_path in paths:
        _load_env_path(env_path)


def _load_env_path(env_path: Path) -> None:
    """Parse a single .env file into os.environ (later files override earlier)."""
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                if key and value:
                    os.environ[key] = value
