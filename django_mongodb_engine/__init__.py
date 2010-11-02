#!/usr/bin/python
# -*- coding: utf-8 -*-

__version__ = (0, 2, 0)
__author__ = "Flavio Percoco Premoli, Alberto Paro, " + \
             "Jonas Haag and contributors"
__contact__ = "django-non-relational@googlegroups.com"
__homepage__ = "http://github.com/django-mongodb-engine/mongodb-engine"
__docformat__ = "restructuredtext"

try:
    #This is not being loaded. Tests needed here
    from django.conf import settings
    import _bootstrap
except ImportError:
    pass
