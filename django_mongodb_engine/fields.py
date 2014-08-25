import json
from django.contrib.gis import forms
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.contrib.gis.geometry.backend import Geometry
from django.db import connections, models
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from gridfs import GridFS
from gridfs.errors import NoFile

# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId 
    
        
from django_mongodb_engine.utils import make_struct


__all__ = ['GridFSField', 'GridFSString']


class GridFSField(models.Field):
    """
    GridFS field to store large chunks of data (blobs) in GridFS.

    Model instances keep references (ObjectIds) to GridFS files
    (:class:`gridfs.GridOut`) which are fetched on first attribute
    access.

    :param delete:
        Whether to delete the data stored in the GridFS (as GridFS
        files) when model instances are deleted (default: :const:`True`).

        Note that this doesn't have any influence on what happens if
        you update the blob value by assigning a new file, in which
        case the old file is always deleted.
    """
    forbids_updates = True

    def __init__(self, *args, **kwargs):
        self._versioning = kwargs.pop('versioning', False)
        self._autodelete = kwargs.pop('delete', not self._versioning)
        if self._versioning:
            import warnings
            warnings.warn("GridFSField versioning will be deprecated on "
                          "version 0.6. If you consider this option useful "
                          "please add a comment on issue #65 with your use "
                          "case.", PendingDeprecationWarning)

        kwargs['max_length'] = 24
        kwargs.setdefault('default', None)
        kwargs.setdefault('null', True)
        super(GridFSField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'gridfs'

    def contribute_to_class(self, model, name):
        # GridFSFields are represented as properties in the model
        # class. Let 'foo' be an instance of a model that has the
        # GridFSField 'gridf'. 'foo.gridf' then calls '_property_get'
        # and 'foo.gridfs = bar' calls '_property_set(bar)'.
        super(GridFSField, self).contribute_to_class(model, name)
        setattr(model, self.attname, property(self._property_get,
                                              self._property_set))
        if self._autodelete:
            models.signals.pre_delete.connect(self._on_pre_delete,
                                              sender=model)

    def _property_get(self, model_instance):
        """
        Gets the file from GridFS using the id stored in the model.
        """
        meta = self._get_meta(model_instance)
        if meta.filelike is None and meta.oid is not None:
            gridfs = self._get_gridfs(model_instance)
            if self._versioning:
                try:
                    meta.filelike = gridfs.get_last_version(filename=meta.oid)
                    return meta.filelike
                except NoFile:
                    pass
            meta.filelike = gridfs.get(meta.oid)
        return meta.filelike

    def _property_set(self, model_instance, value):
        """
        Sets a new value.

        If value is an ObjectID it must be coming from Django's ORM
        internals being the value fetched from the database on query.
        In that case just update the id stored in the model instance.
        Otherwise it sets the value and checks whether a save is needed
        or not.
        """
        meta = self._get_meta(model_instance)
        if isinstance(value, ObjectId) and meta.oid is None:
            meta.oid = value
        else:
            meta.should_save = meta.filelike != value
            meta.filelike = value

    def pre_save(self, model_instance, add):
        meta = self._get_meta(model_instance)
        if meta.should_save:
            gridfs = self._get_gridfs(model_instance)
            if not self._versioning and meta.oid is not None:
                # We're putting a new GridFS file, so get rid of the
                # old one if we weren't explicitly asked to keep it.
                gridfs.delete(meta.oid)
            meta.should_save = False
            if not self._versioning or meta.oid is None:
                meta.oid = gridfs.put(meta.filelike)
            else:
                gridfs.put(meta.filelike, filename=meta.oid)
        return meta.oid

    def _on_pre_delete(self, sender, instance, using, signal, **kwargs):
        """
        Deletes the files associated with this isntance.

        If versioning is enabled all versions will be deleted.
        """
        gridfs = self._get_gridfs(instance)
        meta = self._get_meta(instance)
        try:
            while self._versioning and meta.oid:
                last = gridfs.get_last_version(filename=meta.oid)
                gridfs.delete(last._id)
        except NoFile:
            pass

        gridfs.delete(meta.oid)

    def _get_meta(self, model_instance):
        meta_name = '_%s_meta' % self.attname
        meta = getattr(model_instance, meta_name, None)
        if meta is None:
            meta_cls = make_struct('filelike', 'oid', 'should_save')
            meta = meta_cls(None, None, None)
            setattr(model_instance, meta_name, meta)
        return meta

    def _get_gridfs(self, model_instance):
        model = model_instance.__class__
        return GridFS(connections[model.objects.db].database,
                      model._meta.db_table)


class GridFSString(GridFSField):
    """
    Similar to :class:`GridFSField`, but the data is represented as a
    bytestring on Python side. This implies that all data has to be
    copied **into memory**, so :class:`GridFSString` is for smaller
    chunks of data only.
    """

    def _property_get(self, model):
        filelike = super(GridFSString, self)._property_get(model)
        if filelike is None:
            return ''
        if hasattr(filelike, 'read'):
            return filelike.read()
        return filelike


try:
    # Used to satisfy South when introspecting models that use
    # GridFSField/GridFSString fields. Custom rules could be added
    # if needed.
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(
        [], ['^django_mongodb_engine\.fields\.GridFSField'])
    add_introspection_rules(
        [], ['^django_mongodb_engine\.fields\.GridFSString'])
except ImportError:
    pass


class GeometryField(models.Field):
    """
    The base GIS field -- maps to the OpenGIS Specification Geometry type.

    Based loosely on django.contrib.gis.db.models.fields.GeometryField
    """

    # The OpenGIS Geometry name.
    geom_type = 'GEOMETRY'
    form_class = forms.GeometryField

    lookup_types = {
        'within':     '$geoWithin',
        'intersects': '$geoIntersects',
        'near':       '$near',
        'nearsphere': '$nearSphere',
    }

    description = _("The base GIS field -- maps to the OpenGIS Specification Geometry type.")

    def __init__(self, verbose_name=None, dim=2, **kwargs):
        """
        The initialization function for geometry fields.  Takes the following
        as keyword arguments:

        dim:
         The number of dimensions for this geometry.  Defaults to 2.
        """

        # Mongo GeoJSON are WGS84
        self.srid = 4326

        # Setting the dimension of the geometry field.
        self.dim = dim

        # Setting the verbose_name keyword argument with the positional
        # first parameter, so this works like normal fields.
        kwargs['verbose_name'] = verbose_name

        super(GeometryField, self).__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, Geometry):
            return value
        elif isinstance(value, dict):
            return Geometry(json.dumps(value), self.srid)
        elif isinstance(value, (bytes, six.string_types)):
            return Geometry(value, self.srid)
        raise ValueError('Could not convert to python geometry from value type "%s".' % type(value))

    def get_prep_value(self, value):
        if isinstance(value, Geometry):
            return json.loads(value.json())
        elif isinstance(value, six.string_types):
            return json.loads(value)
        raise ValueError('Could not prep geometry from value type "%s".' % type(value))

    def get_srid(self, geom):
        """
        Returns the default SRID for the given geometry, taking into account
        the SRID set for the field.  For example, if the input geometry
        has no SRID, then that of the field will be returned.
        """
        gsrid = geom.srid  # SRID of given geometry.
        if gsrid is None or self.srid == -1 or (gsrid == -1 and self.srid != -1):
            return self.srid
        else:
            return gsrid

    ### Routines overloaded from Field ###
    def contribute_to_class(self, cls, name, virtual_only=False):
        super(GeometryField, self).contribute_to_class(cls, name, virtual_only)

        # Setup for lazy-instantiated Geometry object.
        setattr(cls, self.attname, GeometryProxy(Geometry, self))

    def db_type(self, connection):
        return self.geom_type

    def formfield(self, **kwargs):
        defaults = {'form_class': self.form_class,
                    'geom_type': self.geom_type,
                    'srid': self.srid,
                    }
        defaults.update(kwargs)
        if (self.dim > 2 and not 'widget' in kwargs and
                not getattr(defaults['form_class'].widget, 'supports_3d', False)):
            defaults['widget'] = forms.Textarea
        return super(GeometryField, self).formfield(**defaults)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if lookup_type not in self.lookup_types:
            raise ValueError('Unknown lookup type "%s".' % lookup_type)
        if not isinstance(value, Geometry):
            raise ValueError('Geometry value is of unsupported type "%s".' % type(value))
        # TODO: extra params???
        return {self.lookup_types[lookup_type]: {'$geometry': json.loads(value.json())}}


# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    geom_type = 'POINT'
    form_class = forms.PointField
    description = _("Point")


class LineStringField(GeometryField):
    geom_type = 'LINESTRING'
    form_class = forms.LineStringField
    description = _("Line string")


class PolygonField(GeometryField):
    geom_type = 'POLYGON'
    form_class = forms.PolygonField
    description = _("Polygon")


class MultiPointField(GeometryField):
    geom_type = 'MULTIPOINT'
    form_class = forms.MultiPointField
    description = _("Multi-point")


class MultiLineStringField(GeometryField):
    geom_type = 'MULTILINESTRING'
    form_class = forms.MultiLineStringField
    description = _("Multi-line string")


class MultiPolygonField(GeometryField):
    geom_type = 'MULTIPOLYGON'
    form_class = forms.MultiPolygonField
    description = _("Multi polygon")


class GeometryCollectionField(GeometryField):
    geom_type = 'GEOMETRYCOLLECTION'
    form_class = forms.GeometryCollectionField
    description = _("Geometry collection")