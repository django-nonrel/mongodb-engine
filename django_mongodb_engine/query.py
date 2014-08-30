from warnings import warn
from django.contrib.gis.db.models.query import GeoQuerySet
from django.contrib.gis.db.models.sql import GeoQuery, GeoWhereNode

from djangotoolbox.fields import RawField, AbstractIterableField, \
    EmbeddedModelField


__all__ = ['A']


DJANGOTOOLBOX_FIELDS = (RawField, AbstractIterableField, EmbeddedModelField)


class A(object):

    def __init__(self, op, value):
        warn("A() queries are deprecated as of 0.5 and will be removed in 0.6.", DeprecationWarning) 

        self.op = op
        self.val = value

    def as_q(self, field):
        if isinstance(field, DJANGOTOOLBOX_FIELDS):
            return '%s.%s' % (field.column, self.op), self.val
        else:
            raise TypeError("Can not use A() queries on %s." %
                            field.__class__.__name__)


class MongoGeoQuery(GeoQuery):
    def __init__(self, model, where=GeoWhereNode):
        super(MongoGeoQuery, self).__init__(model, where)
        self.query_terms |= set(['near'])


class MongoGeoQuerySet(GeoQuerySet):
    def __init__(self, model=None, query=None, using=None):
        super(MongoGeoQuerySet, self).__init__(model=model, query=query, using=using)
        self.query = query or MongoGeoQuery(self.model)