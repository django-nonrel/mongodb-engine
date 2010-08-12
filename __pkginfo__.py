#!/usr/bin/env python
# -*- coding: utf-8 -*-

distname = 'django_mongodb_engine'

numversion = (0, 1, 0)
version = '.'.join([str(num) for num in numversion])

install_requires = ['pymongo', 'django']

pyversions = ["2.5", '2.6', '2.7']

license = 'GPLv2'

author = 'Flavio Percoco Premoli'
author_email = 'flaper87@flaper87.org'
mailinglist = "mailto://%s" % author_email
web = "http://github.com/FlaPer87/django-mongodb-engine"
ftp = ""

short_desc = "A MongoDB backend standing outside django."

long_desc = open("README.rst", "r").read()


from os.path import join
include_dirs = []
