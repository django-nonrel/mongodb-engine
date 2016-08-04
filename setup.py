from distutils.core import setup

import django_mongodb_engine as distmeta


CLASSIFIERS = [
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Internet',
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Operating System :: OS Independent',
]

packages = [
    'django_mongodb_engine',
    'django_mongodb_engine.management',
    'django_mongodb_engine.management.commands',
    'django_mongodb_engine.contrib',
    'django_mongodb_engine.contrib.search'
]

setup(
    name='django-mongodb-engine',
    version='.'.join(map(str, distmeta.__version__)),
    author=distmeta.__author__,
    author_email=distmeta.__contact__,
    url=distmeta.__homepage__,
    license='2-clause BSD',
    description="MongoDB backend for Django",
    install_requires=['pymongo', 'djangotoolbox'],
    packages=packages,
    include_package_data=True,
    classifiers=CLASSIFIERS,
    test_suite='tests',
)
