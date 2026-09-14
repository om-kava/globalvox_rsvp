import os
import sys
import shutil

# Ensure BASE_DIR is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'globalvox_project.settings')

# Instantaneous cold-start seeding: copy pre-migrated seed database to /tmp/db.sqlite3
try:
    tmp_db = '/tmp/db.sqlite3'
    if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) == 0:
        seed_db = os.path.join(BASE_DIR, 'seed.sqlite3')
        if os.path.exists(seed_db):
            shutil.copyfile(seed_db, tmp_db)
except Exception as e:
    print(f"GlobalVox SQLite Seed Notice: {e}")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Alias for Vercel WSGI runner
app = application
