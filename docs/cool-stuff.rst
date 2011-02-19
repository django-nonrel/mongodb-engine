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

The model instance is stored directly in the :class:`lists <ListField>` or 
:class:`dicts <DictField>`, not as an :class:`~djangotoolbox-fields.EmbeddedModelField`.
For more information on embedding models inside :class:`lists <ListField>`'s 
or :class:`dicts <DictField>`'s without automatic referencing see 
:ref:`embedded-objects-list`.

   Example:

   Here we will create an object that has a both a list with a referenced model and
   a list with an embedded model to show the difference when storing each type.

   .. code-block:: python
    
      from django.db import models
      from djangotoolbox.fields import ListField, EmbeddedModelField
      
      class SimpleModel(models.Model):
         value = models.IntegerField()

      class ModelWithReferenedAndEmbeddedObjects(models.Model):
         list_with_reference = ListField()
         list_with_embedded_model = ListField(EmbeddedModelField(SimpleModel))

   Now lets add a ``SimpleModel`` instance to each list ::

      >>> my_simple_model = SimpleModel(value=1)
      >>> reference_model = ModelWithReferenedAndEmbeddedObjects()
      >>> reference_model.list_with_reference.append(my_simple_model)
      >>> reference_model.list_with_embedded_model.append(my_simple_model)
      >>> reference_model.save()

   The resulting document will appear as follows:

   .. code-block:: js

       /* db.sample_modelwithreferenedandembeddedobjects.findOne() */
       {
            "_id" : ObjectId("4d604c2d93577c2d54000001"),
            "list_with_reference" : [
                    {
                            "_app" : "sample",
                            "_model" : "SimpleModel",
                            "_type" : "django",
                            "pk" : "4d604c2d93577c2d54000000"
                    }
            ],
            "list_with_embedded_model" : [
                    {
                            "id" : null,
                            "value" : 1
                    }
            ]
       }
   
   Notice that the ``list_with_reference`` value is set to a list with a dictionary
   containing information about the model and the ID referencing the object in another collection.
   On the other hand, the ``list_with_embedded_model`` value will have the serialized model
   instance contained within the list itself as an embedded model. When working with the
   :class:`list <ListField>` in Python there will be no difference. Each model will be
   automatically initialized and added to the :class:`list <ListField>` for you.

   Note that adding model instances directly to a :class:`list <ListField>`
   or :class:`dict <DictField>`, as is done here, without ``MONGODB_AUTOMATIC_REFERENCING`` set to
   :class:`True` is not supported and you will get an error message if you try to do so.
