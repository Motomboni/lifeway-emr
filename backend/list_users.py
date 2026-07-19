import sys, json;
try:
    from django.core.management import setup_environ
except ImportError:
    pass
# Wait, let's just use django.setup()
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
users = [{'id': tuple.id, 'username': tuple.username} for tuple in User.objects.all()[:5]]
print(json.dumps(users))
