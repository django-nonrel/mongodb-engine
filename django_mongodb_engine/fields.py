from django.db import models
from django.db.models import Field, CharField
from django.utils.translation import ugettext_lazy as _

from pymongo.objectid import ObjectId
from gridfs import GridFS, errors


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


__all__ = ["ListField", "DictField", "SetListField", "SortedListField", ]
__doc__ = "Common module to all nonrel engines"

    
class ListField(Field):
    """A list field that wraps a standard field, allowing multiple instances
    of the field to be used as a list in the database.
    """

    default_error_messages = {
        'invalid': _(u'This value must be a list or an iterable.'),
        'invalid_value': _(u'Invalid value in list.'),
    }

    description = _("List Field")
    _internaltype = None
    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        if 'default' not in kwargs:
            kwargs['default'] = []
        if 'type' in kwargs:
            self._internaltype = kwargs.pop("type")
            
        Field.__init__(self, *args, **kwargs)

    def validate(self, value, model_instance):
        """
        Validates value and throws ValidationError. 
        """
        if not isinstance(value, list) and (not hasattr(value, "__iter__")):
            raise exceptions.ValidationError(self.error_messages['invalid'])

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'])

        if not self.blank and value in validators.EMPTY_VALUES:
            raise exceptions.ValidationError(self.error_messages['blank'])
        if self._internaltype is not None:
            for v in value:
                if not isinstance(v, self._internaltype):
                    raise exceptions.ValidationError(self.error_messages['invalid_value'])
        
    def get_prep_value(self, value):
        if value is None:
            return None
        return list(value)

    def to_python(self, value):
        if value is None:
            return []
        return value

    def get_default(self):
        "Returns the default value for this field."
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        return []

class SortedListField(ListField):
    """A ListField that sorts the contents of its list before writing to
    the database in order to ensure that a sorted list is always
    retrieved.
    """

    description = _("Sorted Field")
    _ordering = None

    def __init__(self, *args, **kwargs):
        if 'ordering' in kwargs.keys():
            self._ordering = kwargs.pop('ordering')
        if 'type' in kwargs:
            self._internaltype = kwargs.pop("type")
        super(SortedListField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value is None:
            return None
        if not isinstance(value, list) and (not hasattr(value, "__iter__")):
            raise exceptions.ValidationError(self.error_messages['invalid'])
        if self._ordering is not None:
            return sorted(value, key=itemgetter(self._ordering))
        return sorted(value)
    
class DictField(Field):
    """A dictionary field that wraps a standard Python dictionary.
    Key cannot contains . or $ for query problems.
    """
    description = _("Dict Field")

    default_error_messages = {
        'invalid': _(u'This value must be a dictionary.'),
        'invalid_key': _(u'Invalid dictionary key name - Keys cannot contains . or $ for query problems'),
    }

    def validate(self, value, model_instance):
        """
        Validates value and throws ValidationError. 
        """
        if not isinstance(value, dict):
            raise exceptions.ValidationError(self.error_messages['invalid'])

        if any(('.' in k or '$' in k) for k in value):
            raise exceptions.ValidationError(self.error_messages['invalid_key'])

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'])

        if not self.blank and value in validators.EMPTY_VALUES:
            raise exceptions.ValidationError(self.error_messages['blank'])

    def get_default(self):
        "Returns the default value for this field."
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        return {}

class SetListField(Field):
    """A list field that allows only one instance for item.
    """

    description = _("List Set Field")
    _internaltype = None
    default_error_messages = {
        'invalid': _(u'This value must be a set.'),
        'invalid_value': _(u'Invalid value in list.'),
    }

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        if 'default' not in kwargs:
            kwargs['default'] = set()
        if 'type' in kwargs:
            self._internaltype = kwargs.pop("type")

        Field.__init__(self, *args, **kwargs)
    def validate(self, value, model_instance):
        """
        Validates value and throws ValidationError. 
        """
        if not isinstance(value, set):
            raise exceptions.ValidationError(self.error_messages['invalid'])

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'])

        if not self.blank and value in validators.EMPTY_VALUES:
            raise exceptions.ValidationError(self.error_messages['blank'])
        if self._internaltype is not None:
            for v in value:
                if not isinstance(v, self._internaltype):
                    raise exceptions.ValidationError(self.error_messages['invalid_value'])

    def get_default(self):
        "Returns the default value for this field."
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        return set()


    def get_db_prep_value(self, value, connection, prepared=False):
        """Returns field's value prepared for interacting with the database
        backend.

        Used by the default implementations of ``get_db_prep_save``and
        `get_db_prep_lookup```
        """
        if not prepared:
            value = list(self.get_prep_value(value))
        return value
    
    def get_prep_value(self, value):
        if value is None:
            return None
        if not isinstance(value, set):
            if hasattr(value, "__iter__"):
                value = set(value)
        return set(value)
    
    def to_python(self, value):
        """
        Converts the input value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value.
        """
        if value is None:
            return set()
        return set(value)

class GridFSField(Field):

    def __init__(self, *args, **kwargs):
        self._as_string = kwargs.pop("as_string", False)
        self._versioning = kwargs.pop("versioning", False)
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

        if value == getattr(model_instance, "_%s_cache" % self.attname, None):
            return oid

        from django.db import connections
        gdfs = GridFS(connections[self.model.objects.db].db_connection.db)
        

        if not self._versioning and not oid is None:
            gdfs.delete(oid)

        if not self._as_string:
            value = value.seek(0)
            value = value.read()
        
        oid = gdfs.put(value)
        setattr(self, "_%s_oid" % self.attname, oid)
        setattr(self, "_%s_cache" % self.attname, value)

        return oid
