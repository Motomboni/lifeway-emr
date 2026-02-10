"""
Helper script to load environment variables from .env file.

This script can be imported in settings.py to load .env variables.
Alternatively, you can use python-decouple or django-environ packages.
"""
import os
from pathlib import Path

def load_env_file(env_file='.env'):
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
    
    env_path = None
    if backend_env.exists():
        env_path = backend_env
    elif root_env.exists():
        env_path = root_env
    else:
        return  # No .env file found
    
    if not env_path.exists():
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Set environment variable if not already set
                if key and value and key not in os.environ:
                    os.environ[key] = value
