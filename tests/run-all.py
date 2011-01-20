#!/usr/bin/python
import subprocess
import settings

exit(subprocess.Popen(['./manage.py', 'test'] + settings.INSTALLED_APPS).wait())
