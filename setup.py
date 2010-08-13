from setuptools import setup, find_packages
import os

DESCRIPTION = "A MongoDB backend standing outside django (>= 1.2)"

LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

pkginfo = __import__("__pkginfo__")

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

setup(name='django_mongodb_engine',
      version= pkginfo.version,
      packages=find_packages(),
      author='Flavio Percoco Premoli - Alberto Paro',
      author_email='flaper87@{nospam}flaper87.org',
      url='http://github.com/FlaPer87/django-mongodb-engine/',
      license='MIT',
      include_package_data=True,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      platforms=['any'],
      classifiers=CLASSIFIERS,
      install_requires=['pymongo'],
      test_suite='tests',
)
