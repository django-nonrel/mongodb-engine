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
    name=pkginfo.distname,
    version=pkginfo.version,
    author=pkginfo.author,
    author_email=pkginfo.author_email,
    url=pkginfo.web,
    license=license,
    description=pkginfo.short_desc,
    long_description=pkginfo.long_desc,

    platforms=['any'],
    install_requires=pkginfo.install_requires,

    packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
    include_package_data=True,
    classifiers=CLASSIFIERS,
    test_suite='tests',
)
