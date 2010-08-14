from setuptools import setup, find_packages
import os

pkginfo = __import__("__pkginfo__")

install_requires = pkginfo.install_requires

CLASSIFIERS = [
    'Topic :: Internet',
    'Topic :: Database',
    'Operating System :: POSIX',
    'Programming Language :: Python',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'License :: OSI Approved :: BSD License',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

for ver in pkginfo.pyversions:
    CLASSIFIERS.append('Programming Language :: Python :: %s' % ver)
    

setup(name='django_mongodb_engine',
      version= pkginfo.version,
      packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
      author='Flavio Percoco Premoli - Alberto Paro',
      author_email='flaper87@{nospam}flaper87.org',
      url='http://github.com/FlaPer87/django-mongodb-engine/',
      license='MIT',
      include_package_data=True,
      description=pkginfo.short_desc,
      long_description=pkginfo.long_desc,
      platforms=['any'],
      classifiers=CLASSIFIERS,
      install_requires=install_requires,
      test_suite='tests',
)
