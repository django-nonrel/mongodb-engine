import re
import time
from pymongo import ASCENDING
from django.conf import settings
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

def make_index_list(indexes):
    for index in indexes:
        if not isinstance(index, tuple):
            index = index, ASCENDING
        yield index

class CollectionDebugWrapper(object):
    def __init__(self, collection, db_alias):
        self.collection = collection
        self.alias = db_alias

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
                if len(settings.DATABASES) > 1:
                    msg = self.alias + '.' + msg
                logger.debug(msg, extra={'duration' : duration})
            return result
        return wrapper

    find = logging_wrapper('find')
    save = logging_wrapper('save')
    remove = logging_wrapper('remove')
    update = logging_wrapper('update', npositional=2)
    map_reduce = logging_wrapper('map_reduce', npositional=None)

    del logging_wrapper
