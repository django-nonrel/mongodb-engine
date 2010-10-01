from setuptools import setup, find_packages

pkginfo = __import__('__pkginfo__')

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


setup(
    name='django_mongodb_engine',
    version= pkginfo.version,
    packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
    author='Flavio Percoco Premoli, Alberto Paro and contributors',
    author_email='django-mongodb-engine@lophus.org',
    url='http://github.com/django-mongodb-engine/mongodb-engine',
    license='2-clause BSD',
    include_package_data=True,
    description=pkginfo.short_desc,
    long_description=pkginfo.long_desc,
    platforms=['any'],
    classifiers=CLASSIFIERS,
    install_requires=pkginfo.install_requires,
    test_suite='tests',
)
