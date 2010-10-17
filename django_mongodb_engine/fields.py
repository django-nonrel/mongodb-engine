from future_builtins import zip
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.importlib import import_module
from pymongo.objectid import ObjectId
from gridfs import GridFS
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from djangotoolbox.fields import *

__all__ = ['GridFSField', 'EmbeddedModelField']

class EmbeddedModelField(DictField):
    """
    Field that allows you to embed a model instance.

    :param model: The model class that shall be embedded

    For example, we want to namespace everything that belongs to a customer's
    address into the ``address`` field::

        class Address(models.Model):
            street = models.CharField(max_length=200)
            postal_code = models.IntegerField()
            city = models.CharField(max_length=100)

        class Customer(models.Model):
            name = models.CharField(max_length=100)
            last_name = models.CharField(max_length=100)
            address = EmbeddedModelField(Address)

    :class:`EmbeddedModelField` behaves similar to relations::

        bob = Customer(
           name='Bob', last_name='Laxley',
           address=Address(street='Behind the Mountains 23',
                           postal_code=1337, city='Blurginson')
        )
        assert bob.address.postal_code == 1337

    When saved, embedded models are serialized to dictionaries. When queried,
    the dictionary will be unserialized back to a model instance::

        bob.save()
        bob_from_db = Customer.objects.get(name='Bob')
        assert bob_from_db.address.city == 'Blurginson'
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, model, *args, **kwargs):
        self.embedded_model = model
        super(EmbeddedModelField, self).__init__(*args, **kwargs)


    def get_db_prep_save(self, model_instance, connection):
        if not model_instance:
            return None

        values = {}
        for field in self.embedded_model._meta.fields:
            values[field.name] = field.get_db_prep_save(
                    field.pre_save(model_instance, model_instance.id is None),
                    connection=connection
                )
        return values

    def get_db_prep_value(self, model_instance, connection, prepared=False):
        if model_instance is None:
            return None

        values = {}
        for field in self.embedded_model._meta.fields:
            values[field.name] = field.get_db_prep_value(
                getattr(model_instance, field.name),
                connection=connection,
                prepared=prepared
            )
        return values

    def to_python(self, values):
        if isinstance(values, dict):
            if not values:
                return None

            # In version 0.2, the layout of the serialized model instance changed.
            # Cleanup up old instances from keys that aren't used any more.
            for key in ('_app', '_model', '_id'):
                values.pop(key, None)

            assert len(values.keys()) == len(self.embedded_model._meta.fields), 'corrupt embedded field'

            model = self.embedded_model()
            for k,v in values.items():
                setattr(model, k, v)
            return model

        return values


class GridFSField(models.CharField):

    def __init__(self, *args, **kwargs):
        self._as_string = kwargs.pop("as_string", False)
        self._versioning = kwargs.pop("versioning", False)
        kwargs["max_length"] = 255
        super(GridFSField, self).__init__(*args, **kwargs)


    def contribute_to_class(self, cls, name):
        super(GridFSField, self).contribute_to_class(cls, name)

        att_oid_name = "_%s_oid" % name
        att_cache_name = "_%s_cache" % name
        att_val_name = "_%s_val" % name
        as_string = self._as_string

        def _get(self):
            from django.db import connections
            gdfs = GridFS(connections[self.__class__.objects.db].db_connection.db)
            if not hasattr(self, att_cache_name) and not getattr(self, att_val_name, None) and getattr(self, att_oid_name, None):
                val = gdfs.get(getattr(self, att_oid_name))
                if as_string:
                    val = val.read()
                setattr(self, att_cache_name, val)
                setattr(self, att_val_name, val)
            return getattr(self, att_val_name, None)

        def _set(self, val):
            if isinstance(val, ObjectId) and not hasattr(self, att_oid_name):
                setattr(self, att_oid_name, val)
            else:
                if isinstance(val, unicode):
                    val = val.encode('utf8', 'ignore')

                if isinstance(val, basestring) and not as_string:
                    val = StringIO(val)

                setattr(self, att_val_name, val)

        setattr(cls, self.attname, property(_get, _set))


    def db_type(self, connection):
        return "gridfs"

    def pre_save(self, model_instance, add):
        oid = getattr(model_instance, "_%s_oid" % self.attname, None)
        value = getattr(model_instance, "_%s_val" % self.attname, None)

        if not getattr(model_instance, "id"):
            return u''

        if value == getattr(model_instance, "_%s_cache" % self.attname, None):
            return oid

        from django.db import connections
        gdfs = GridFS(connections[self.model.objects.db].db_connection.db)


        if not self._versioning and not oid is None:
            gdfs.delete(oid)

        if not self._as_string:
            value.seek(0)
            value = value.read()

        oid = gdfs.put(value)
        setattr(self, "_%s_oid" % self.attname, oid)
        setattr(self, "_%s_cache" % self.attname, value)

        return oid
