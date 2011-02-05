Other Cool Stuff
================

Included MongoDB Batteries
--------------------------
For usage examples, see `tests/contrib/tests.py`_.

.. _tests/contrib/tests.py: https://github.com/django-mongodb-engine/mongodb-engine/blob/master/tests/contrib/tests.py

.. autoclass:: django_mongodb_engine.contrib.MongoDBManager


.. _raw-queries-and-updates:

Raw Queries/Updates
~~~~~~~~~~~~~~~~~~~
.. versionadded:: 0.3

.. autoclass:: django_mongodb_engine.contrib.RawQueryMixin
   :members:


.. _mapreduce:

Map/Reduce Support
~~~~~~~~~~~~~~~~~~
.. versionadded:: 0.2

.. automodule:: django_mongodb_engine.contrib.mapreduce
   :members:


.. _mongodb-fields:

Fields
------
.. automodule:: django_mongodb_engine.fields
   :members:


.. _collection-options:

Collection Options
------------------
Collection flags can be set in a :class:`MongoMeta` attribute in a model,
similar to Django's :class:`Meta` class:

.. code-block:: python

   class MyModel(models.Model):
       # your fields here

       class MongoMeta:
           # your flags here

Those flags can be:

``index_together`` (default: ``[]``)
   A list of dictionaries containing an item with the key *field* and a list of
   field names or :samp:`({field name}, {index direction})` tuples to
   index together, optionally containing keyword arguments to pass to
   :meth:`pymongo.Collection.ensure_index`. For example, ::

      index_together = [{'fields' : ['name', ('last_name', pymongo.DESCENDING)],
                         'name' : 'name-lastname-index'}]

   results in this call::

      target_collection.ensure_index([('name', 1), ('last_name', -1)], name='name-lastname-index')

``descending_indexes`` (default: ``[]``)
   A list of fields whose index shall be descending rather than ascending.
   For example, ::

      class MyModel(models.Model):
          a = models.CharField(db_index=True)
          b = models.CharField(db_index=True)

          class MongoMeta:
              descending_indexes = ['b']

   would create an ascending index on field ``a`` and a descending one on ``b``.

``capped`` (default: :const:`False`)
   A boolean specifying whether the collection for the model shall be capped.

``collection_size`` and ``collection_max`` (default: unset)
   If using a ``capped`` collection, those two options specify the size (in bytes)
   and the maximum number of objects of the capped collection, respectively.


.. _model_referencing:

Automatic Model Instance (De)Referencing
----------------------------------------
If you set the ``MONGODB_AUTOMATIC_REFERENCING`` option to :class:`True` in
your :file:`settings.py`, django-mongodb-engine automatically references
model instances in :class:`lists <ListField>` or :class:`dicts <DictField>` on
saves and dereferences them when you access an attribute.

.. todo::

   Example
