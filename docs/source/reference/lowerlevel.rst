Lower-Level API
===============
::

   from django_mongodb_engine.contrib import MongoDBManager

   class FooModel(models.Model):
       ...
       objects = MongoDBManager()

::

   >>> FooModel.objects.raw_query(...)
   >>> FooModel.objects.raw_update(...)

.. currentmodule:: django_mongodb_engine.contrib

.. automethod:: MongoDBManager.raw_query

.. automethod:: MongoDBManager.raw_update
