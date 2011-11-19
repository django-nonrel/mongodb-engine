.. the following warning is a 1:1 copy from topics/lowerlevel.rst
.. warning::

   These APIs are available for MongoDB only, so using any of these features
   breaks portability to other non-relational databases (Google App Engine,
   Cassandra, Redis, ...). For the sake of portability you should try to avoid
   database-specific features whenever possible.

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

.. automethod:: MongoDBManager.distinct
