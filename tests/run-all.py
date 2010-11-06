#!/usr/bin/python
import os
import settings

for app in settings.INSTALLED_APPS:
    os.system('./manage.py test %s' % app)
