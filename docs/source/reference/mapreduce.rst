Map/Reduce
==========
::

   from django_mongodb_engine.contrib import MongoDBManager

   class MapReduceableModel(models.Model):
       ...
       objects = MongoDBManager()

::

   >>> MapReduceableModel.objects.filter(...).map_reduce(...)

.. currentmodule:: django_mongodb_engine.contrib

.. TODO Should be documented as MongoDBManager.map_reduce
.. automethod:: MongoDBQuerySet.map_reduce(...)

.. automethod:: MongoDBQuerySet.inline_map_reduce(...)

.. autoclass:: MapReduceResult
