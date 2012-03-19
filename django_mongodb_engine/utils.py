import re
import time

from django.conf import settings
from django.db.backends.util import logger

from pymongo import ASCENDING
from pymongo.cursor import Cursor


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
    if isinstance(indexes, basestring):
        indexes = [indexes]
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

    def profile_call(self, func, args=(), kwargs={}):
        start = time.time()
        retval = func(*args, **kwargs)
        duration = time.time() - start
        return duration, retval

    def log(self, op, duration, args, kwargs=None):
        args = ' '.join(str(arg) for arg in args)
        msg = '%s.%s (%.2f) %s' % (self.collection.name, op, duration, args)
        kwargs = dict((k, v) for k, v in kwargs.iteritems() if v)
        if kwargs:
            msg += ' %s' % kwargs
        if len(settings.DATABASES) > 1:
            msg = self.alias + '.' + msg
        logger.debug(msg, extra={'duration': duration})

    def find(self, *args, **kwargs):
        if not 'slave_okay' in kwargs and self.collection.slave_okay:
            kwargs['slave_okay'] = True
        return DebugCursor(self, self.collection, *args, **kwargs)

    def logging_wrapper(method):

        def wrapper(self, *args, **kwargs):
            func = getattr(self.collection, method)
            duration, retval = self.profile_call(func, args, kwargs)
            self.log(method, duration, args, kwargs)
            return retval

        return wrapper

    save = logging_wrapper('save')
    remove = logging_wrapper('remove')
    update = logging_wrapper('update')
    map_reduce = logging_wrapper('map_reduce')
    inline_map_reduce = logging_wrapper('inline_map_reduce')

    del logging_wrapper


class DebugCursor(Cursor):

    def __init__(self, collection_wrapper, *args, **kwargs):
        self.collection_wrapper = collection_wrapper
        super(DebugCursor, self).__init__(*args, **kwargs)

    def _refresh(self):
        super_meth = super(DebugCursor, self)._refresh
        if self._Cursor__id is not None:
            return super_meth()
        # self.__id is None: first time the .find() iterator is
        # entered. find() profiling happens here.
        duration, retval = self.collection_wrapper.profile_call(super_meth)
        kwargs = {'limit': self._Cursor__limit, 'skip': self._Cursor__skip,
                  'sort': self._Cursor__ordering}
        self.collection_wrapper.log('find', duration, [self._Cursor__spec],
                                    kwargs)
        return retval
