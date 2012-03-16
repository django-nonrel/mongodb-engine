Model Options
=============

In addition to Django's `default Meta options`_, Django MongoDB Engine supports
various options specific to MongoDB through a special ``class MongoMeta``. ::

   class FooModel(models.Model):
       ...
       class MongoMeta:
           # Mongo options here
           ...

Indexes
-------
Django MongoDB Engine already understands the standard
:attr:`~django.db.models.Field.db_index` and
:attr:`~django.db.models.Options.unique_together` options and generates the
corresponding MongoDB indexes on ``syncdb``.

To make use of other index features, like multi-key indexes and Geospatial
Indexing, additional indexes can be specified using the ``indexes`` setting. ::

   class Club(models.Model):
      location = ListField()
      rating = models.FloatField()
      admission = models.IntegerField()
      ...
      class MongoMeta:
         indexes = [
            [('rating', -1)],
            [('rating', -1), ('admission', 1)],
            {'fields': [('location', '2d')], 'min': -42, 'max': 42},
         ]

``indexes`` can be specified in two ways:

* The simple "without options" form is a list of ``(field, direction)`` pairs.
  For example, a single ascending index (the same thing you get using ``db_index``)
  is expressed as ``[(field, 1)]``. A multi-key, descending index can be written
  as ``[(field1, -1), (field2, -1), ...]``.
* The second form is slightly more verbose but takes additional MongoDB index
  options. A descending, sparse index for instance may be expressed as
  ``{'fields': [(field, -1)], 'sparse': True}``.


Capped Collections
------------------
Use the ``capped`` option and ``collection_size`` (and/or ``collection_max``)
to limit a collection in size (and/or document count), new documents replacing
old ones after reaching one of the limit sets.

For example, a logging collection fixed to 50MiB could be defined as follows::

   class LogEntry(models.Model):
       timestamp = models.DateTimeField()
       message = models.TextField()
       ...
       class MongoMeta:
           capped = True
           collection_size = 50*1024*1024

.. _default Meta options: http://docs.djangoproject.com/en/dev/topics/db/models/#meta-options
.. _sparse: http://www.mongodb.org/display/DOCS/Indexes#Indexes-SparseIndexes
