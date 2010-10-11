#!/usr/bin/env python
import os, sys
from django.core.management import execute_manager
# dirty hack to get the backend working.
sys.path.insert(0, os.path.abspath('./..'))
sys.path.insert(0, os.path.abspath('./../..'))

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django_mongodb_engine._bootstrap

if __name__ == "__main__":
    execute_manager(settings)
