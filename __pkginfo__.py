#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import codecs
import django_mongodb_engine as distmeta

distname = 'django_mongodb_engine'

numversion = (0, 1, 1)
version = distmeta.__version__

install_requires = ['pymongo', 'django>=1.2', 'djangotoolbox']

pyversions = ["2", "2.4", "2.5", '2.6', '2.7']

license = 'GPLv2'

author = distmenta.__author__ 
author_email = distmeta.__contact__
web = distmeta.__homepage__
docformat = distmeta.__docformat__ 

short_desc = "A MongoDB backend standing outside django."

if os.path.exists("README.rst"):
    long_desc = codecs.open("README.rst", "r", "utf-8").read()
else:
    long_desc = "See http://pypi.python.org/pypi/django_mongodb_engine/"


from os.path import join
include_dirs = []
