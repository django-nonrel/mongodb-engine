Model Options
=============

In addition to Django's `default Meta options`, Django MongoDB Engine supports
various options specific to MongoDB through a special ``class MongoMeta``. ::

   class FooModel(models.Model):
       ...
       class MongoMeta:
           # mongo options here
           ...

Indexes
-------
Make use of MongoDB's wide variety of indexes.

``index_together``
   **Form 1**: A tuple of field names or :samp:`({field name}, {index direction})`
   tuples to index together. For instance, ::

      class MongoMeta:
          index_together = ['name', ('last_name', pymongo.DESCENDING)]

   results in this call::

      collection.ensure_index([('name', 1), ('last_name', -1)])

   (``pymongo.DESCENDING`` being the same as -1)

   **Form 2**: A list of dictionaries containing an item with the key *field*
   and a list of field names or :samp:`({field name}, {index direction})` tuples
   to index together as value, optionally containing keyword arguments to pass to
   :meth:`pymongo.Collection.ensure_index`. For example, ::

      index_together = [{'fields' : ['name', ('last_name', pymongo.DESCENDING)],
                         'name' : 'name-lastname-index'}]

   results in this call::

      collection.ensure_index([('name', 1), ('last_name', -1)], name='name-lastname-index')

``descending_indexes``
   A list of fields whose index shall be descending rather than ascending.
   For example, ::

      class FooModel(models.Model):
          a = models.CharField(db_index=True)
          b = models.CharField(db_index=True)

          class MongoMeta:
              descending_indexes = ['b']

   would create an ascending index on field ``a`` and a descending one on ``b``.

``sparse_indexes``
   A list of field names or tuples of field names whose index should be sparse_.
   This example defines a sparse index on `a` and a sparse index on `b, c`::

      class FooModel(models.Model):
          a = models.IntegerField(null=True)
          b = models.IntegerField(null=True)
          c = models.IntegerField(null=True)

          class MongoMeta:
              index_together = ('b', 'c')
              sparse_indexes = ['a', ('b', 'c')]

Capped Collections
------------------
Use the ``capped`` option and ``collection_size`` (and/or ``collection_max``)
to limit a collection in size (and/or document count), new documents replacing
old ones after reaching one of the limit sets.

For example, a logging collection fixed to 50MiB could be defined as follows::

   class LogEntry(models.Model):
       timestamp = models.DateTimeField()
       message = models.CharField()
       ...
       class MongoMeta:
           capped = True
           collection_size = 50*1024*1024

.. _default Meta options: http://docs.djangoproject.com/en/dev/topics/db/models/#meta-options
.. _sparse: http://www.mongodb.org/display/DOCS/Indexes#Indexes-SparseIndexes
