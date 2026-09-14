import os
import sys
import shutil
import traceback

# Ensure root project directory is in python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'globalvox_project.settings')

# Instantaneous cold-start seeding: copy pre-migrated seed database to /tmp/db.sqlite3
try:
    tmp_db = '/tmp/db.sqlite3'
    if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) == 0:
        seed_db = os.path.join(parent_dir, 'seed.sqlite3')
        if os.path.exists(seed_db):
            shutil.copyfile(seed_db, tmp_db)
except Exception as e:
    print(f"GlobalVox SQLite Seed Notice: {e}")

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
        return [f"GlobalVox Serverless Runtime Error:\n\n{tb}".encode('utf-8')]

# Export both 'application' and 'app' to satisfy any Vercel Python runner variation
app = application
