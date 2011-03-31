import re
import time

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.db import connections
from django.db.backends.util import logger

def first(test_func, iterable):
    for item in iterable:
        if test_func(item):
            return item

def safe_regex(regex, *re_args, **re_kwargs):
    def wrapper(value):
        return re.compile(regex % re.escape(value), *re_args, **re_kwargs)
    wrapper.__name__ = 'safe_regex (%r)' % regex
    return wrapper

def make_struct(*attrs):
    class _Struct(object):
        __slots__ = attrs
        def __init__(self, *args):
            for attr, arg in zip(self.__slots__, args):
                setattr(self, attr, arg)
    return _Struct

# MongoDB related stuff:

def get_databases():
    default_database = None
    databases = []
    for name, databaseopt in settings.DATABASES.iteritems():
        if databaseopt['ENGINE'] == 'django_mongodb_engine':
            databases.append(name)
            if databaseopt.get('IS_DEFAULT'):
                if default_database is None:
                    default_database = name
                else:
                    raise ImproperlyConfigured("There can be only one default MongoDB database")

    if not databases:
        raise ImproperlyConfigured("No MongoDB database found in settings.DATABASES")

    if default_database is None:
        default_database = databases[0]

    return default_database, databases

def get_default_database():
    return get_databases()[0]

def get_default_db_connection():
    return connections[get_default_database()].database

class CollectionDebugWrapper(object):
    def __init__(self, collection):
        self.collection = collection

    def __getattr__(self, attr):
        return getattr(self.collection, attr)

    def logging_wrapper(method, npositional=1):
        def wrapper(self, *args, **kwargs):
            if npositional is not None:
                assert len(args) == npositional
            start = time.time()
            try:
                result = getattr(self.collection, method)(*args, **kwargs)
            finally:
                duration = time.time() - start
                msg = '%s.%s (%.3f) %s' % (self.collection.name, method, duration,
                                           ' '.join(str(arg) for arg in args))
                if any(kwargs.itervalues()):
                    msg += ' %s' % kwargs
                logger.debug(msg, extra={'duration' : duration})
            return result
        return wrapper

    find = logging_wrapper('find')
    save = logging_wrapper('save')
    remove = logging_wrapper('remove')
    update = logging_wrapper('update', npositional=2)
    map_reduce = logging_wrapper('map_reduce', npositional=None)

    del logging_wrapper
