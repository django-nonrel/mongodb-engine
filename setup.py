from setuptools import setup, find_packages

import django_mongodb_engine as distmeta


setup(name='django-mongodb-engine',
    version='.'.join(map(str, distmeta.__version__)),
    author=distmeta.__author__,
    author_email=distmeta.__contact__,
    url=distmeta.__homepage__,
    license='2-clause BSD',
    description="MongoDB backend for Django",
    install_requires=['pymongo', 'djangotoolbox>=1.6.0'],
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Database',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
