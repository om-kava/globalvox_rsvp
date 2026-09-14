import os
import sys
import traceback
import shutil

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'globalvox_project.settings')

import_error = None
_django_app = None

try:
    # Ensure /tmp/db.sqlite3 is initialized
    tmp_db = '/tmp/db.sqlite3'
    if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) == 0:
        seed_db = os.path.join(parent_dir, 'seed.sqlite3')
        if os.path.exists(seed_db):
            shutil.copyfile(seed_db, tmp_db)
        else:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('migrate', interactive=False)
            call_command('create_default_manager')

    from django.core.wsgi import get_wsgi_application
    _django_app = get_wsgi_application()

except Exception as e:
    import_error = traceback.format_exc()
    print(f"Startup Failure:\n{import_error}")

def application(environ, start_response):
    if import_error or _django_app is None:
        status = '200 OK'
        headers = [('Content-Type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family: monospace; padding: 2rem; background: #0f172a; color: #f87171;">
    <h1 style="color: #ef4444;">Serverless Startup Import Error</h1>
    <pre style="background: #1e293b; padding: 1.5rem; border-radius: 8px; color: #fecaca; white-space: pre-wrap; font-size: 14px;">{import_error}</pre>
</body>
</html>"""
        return [html.encode('utf-8')]

    try:
        return _django_app(environ, start_response)
    except Exception as e:
        tb = traceback.format_exc()
        status = '200 OK'
        headers = [('Content-Type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family: monospace; padding: 2rem; background: #0f172a; color: #f87171;">
    <h1 style="color: #ef4444;">Serverless Runtime Request Error</h1>
    <pre style="background: #1e293b; padding: 1.5rem; border-radius: 8px; color: #fecaca; white-space: pre-wrap; font-size: 14px;">{tb}</pre>
</body>
</html>"""
        return [html.encode('utf-8')]

app = application
