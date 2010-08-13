#!/usr/bin/python
# -*- coding: utf-8 -*-

from django_mongodb_engine import *

from django.conf import settings

if not "django_mongodb_engine" in settings.INSTALLED_APPS:
    settings.INSTALLED_APPS.insert(0, "django_mongodb_engine")