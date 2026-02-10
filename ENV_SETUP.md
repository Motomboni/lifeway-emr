# Environment Variables Setup

## .env File Created ✅

A `.env` file has been created in the project root with sample configuration values.

## Important Notes

### Loading .env File

The Django settings file now includes automatic `.env` file loading via `load_env.py`. However, for better production use, consider installing one of these packages:

**Option 1: python-decouple (Recommended)**
```bash
pip install python-decouple
```

Then in `settings.py`:
```python
from decouple import config

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
```

**Option 2: django-environ**
```bash
pip install django-environ
```

Then in `settings.py`:
```python
import environ

env = environ.Env()
environ.Env.read_env()

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG', default=True)
```

**Option 3: python-dotenv**
```bash
pip install python-dotenv
```

Then in `settings.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Current Implementation

The current setup uses a simple `load_env.py` script that automatically loads variables from `.env` when Django starts. This works for development but for production, use one of the packages above.

## .env File Location

The `.env` file is located at:
```
C:\Users\Damian Motomboni\Desktop\Modern EMR\.env
```

## Configuration Values

The `.env` file includes:

- **Django Settings**: SECRET_KEY, DEBUG, ALLOWED_HOSTS
- **Database**: SQLite (development) or PostgreSQL (production)
- **Email**: Console backend (development)
- **SMS**: Console mode (development)
- **Twilio**: Placeholder values (update with real credentials)
- **Backup**: Retention days setting

## Next Steps

1. **Review the `.env` file** and update values as needed
2. **For production**: 
   - Change SECRET_KEY to a random string
   - Set DEBUG=False
   - Configure real database credentials
   - Set up SMTP email
   - Configure Twilio credentials (if using SMS/Video)
3. **Install a proper .env loader** (python-decouple recommended)

## Security

- ✅ `.env` file is in `.gitignore` (not committed to version control)
- ⚠️ Never commit `.env` to git
- ⚠️ Use strong passwords in production
- ⚠️ Rotate secrets regularly

## Testing

To verify the .env file is loading:

```python
# In Django shell
python manage.py shell
>>> import os
>>> os.environ.get('SECRET_KEY')
'django-insecure-change-this-in-production-use-a-random-string-here'
```
