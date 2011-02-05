#!/usr/bin/python
import subprocess

import settings
#subprocess.Popen(['./manage.py', 'test'] + settings.INSTALLED_APPS).wait()

import settings_dbindexer
subprocess.Popen(['./manage.py', 'test', '--settings', 'settings_dbindexer']
                 + settings_dbindexer.INSTALLED_APPS).wait()

subprocess.Popen(['./manage.py', 'test', '--settings', 'settings_ref']
                 + settings.INSTALLED_APPS).wait()

#import settings_sqlite
#subprocess.Popen(['./manage.py --settings settings_sqlite', 'test']
#                 + settings_sqlite.INSTALLED_APPS).wait()