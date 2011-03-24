#!/usr/bin/python
import os
import sys
import subprocess
check_call = subprocess.check_call

# Run some basic tests outside Django's test environment
check_call(['python', '-c', 'from general.models import Blog\n'
                            'Blog.objects.create()\n'
                            'Blog.objects.all().delete()\n'
                            'Blog.objects.update()'],
           env=dict(os.environ, DJANGO_SETTINGS_MODULE='settings', PYTHONPATH='..'))

import settings

check_call(['./manage.py', 'test'] + settings.INSTALLED_APPS)

if 'short' in sys.argv:
    exit()

check_call(['./manage.py', 'syncdb', '--noinput'])

import settings_dbindexer
check_call(['./manage.py', 'test', '--settings', 'settings_dbindexer']
           + settings_dbindexer.INSTALLED_APPS)

check_call(['./manage.py', 'test', '--settings', 'settings_debug']
           + settings.INSTALLED_APPS)

#import settings_sqlite
#check_call(['./manage.py --settings settings_sqlite', 'test']
#           + settings_sqlite.INSTALLED_APPS)
