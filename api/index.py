import os
import sys

# Ensure root project directory is in python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'globalvox_project.settings')

# Automatic cold-start migration and account seeding on serverless deployment
try:
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', interactive=False)
    call_command('create_default_manager', interactive=False)
except Exception as e:
    print(f"Startup notice: {e}")

from globalvox_project.wsgi import app
