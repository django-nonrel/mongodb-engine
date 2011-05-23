Fields
======

This is a reference of both fields that are implemented in djangotoolbox_ and
fields specific to MongoDB.

(In signatures, ``...`` represents arbitrary positional and keyword arguments
that are passed to :class:`django.db.models.Field`.)

in :mod:`djangotoolbox`
---------------------------
.. currentmodule:: djangotoolbox.fields

.. autoclass:: ListField(item_field=None, ...)

.. autoclass:: SetField(item_field=None, ...)

.. autoclass:: DictField(item_field=None, ...)

.. autoclass:: EmbeddedModelField(embedded_model=None, ...)

.. autoclass:: BlobField(...)

in :mod:`django_mongodb_engine`
-----------------------------------
.. currentmodule:: django_mongodb_engine.fields

.. autoclass:: GridFSField(delete=True, versioning=False, ...)

.. autoclass:: GridFSString(delete=True, versioning=False, ...)


.. _djangotoolbox: http://allbuttonspressed.com/projects/djangotoolbox
