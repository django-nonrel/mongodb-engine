#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

VERSION = (0, 1, 1)

__version__ = ".".join(map(str, VERSION[0:3])) + "".join(VERSION[3:])
__author__ = "Flavio Percoco Premoli"
__contact__ = "flaper87@flaper87.org"
__homepage__ = "http://github.com/FlaPer87/django-mongodb-engine/"
__docformat__ = "restructuredtext"
