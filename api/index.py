import os
import sys
import traceback

# Ensure root project directory is in python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'globalvox_project.settings')

# Automatic cold-start migration and account seeding on serverless deployment
startup_error = None
try:
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', interactive=False)
    call_command('create_default_manager')
except Exception as e:
    startup_error = traceback.format_exc()
    print(f"GlobalVox Startup Notice:\n{startup_error}")

from django.core.wsgi import get_wsgi_application
_django_app = get_wsgi_application()

def application(environ, start_response):
    try:
        return _django_app(environ, start_response)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"WSGI Invocation Exception:\n{tb}")
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, headers)
        err_msg = f"GlobalVox Serverless Runtime Error:\n\n{tb}"
        if startup_error:
            err_msg += f"\n\nCold-start Diagnostic Log:\n{startup_error}"
        return [err_msg.encode('utf-8')]

# Export both 'application' and 'app' to satisfy any Vercel Python runner variation
app = application
