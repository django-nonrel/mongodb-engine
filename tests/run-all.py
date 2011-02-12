#!/usr/bin/python
import sys
import subprocess
check_call = subprocess.check_call

import settings

check_call(['./manage.py', 'test'] + settings.INSTALLED_APPS)

if 'short' in sys.argv:
    exit()

check_call(['./manage.py', 'syncdb', '--noinput'])

import settings_dbindexer
check_call(['./manage.py', 'test', '--settings', 'settings_dbindexer']
           + settings_dbindexer.INSTALLED_APPS)

check_call(['./manage.py', 'test', '--settings', 'settings_ref']
           + settings.INSTALLED_APPS)

check_call(['./manage.py', 'test', '--settings', 'settings_debug']
           + settings.INSTALLED_APPS)

#import settings_sqlite
#check_call(['./manage.py --settings settings_sqlite', 'test']
#           + settings_sqlite.INSTALLED_APPS)
