from setuptools import setup, find_packages
import codecs
import django_mongodb_engine as distmeta


CLASSIFIERS = [
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python',
    'Topic :: Internet',
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Operating System :: OS Independent',
]

for ver in ['2', '2.4', '2.5', '2.6', '2.7']:
    CLASSIFIERS.append('Programming Language :: Python :: %s' % ver)


setup(
    name='django-mongodb-engine',
    version='.'.join(map(str, distmeta.__version__)),
    author=distmeta.__author__,
    author_email=distmeta.__contact__,
    url=distmeta.__homepage__,
    license='2-clause BSD',
    description= "A MongoDB backend standing outside django.",
    long_description=codecs.open('README.rst', 'r', 'utf-8').read(),

    platforms=['any'],
    install_requires=['pymongo', 'djangotoolbox'],

    packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
    include_package_data=True,
    classifiers=CLASSIFIERS,
    test_suite='tests',
)
