======================================
 :mod:`django_mongodb_engine.contrib`
======================================

The :mod:`django_mongodb_engine.contrib` module contains the :class:`MongoDBManager`
class, which provides support for performing MapReduce queries on Django models.
(TODO: + execjs?).

.. autoclass:: django_mongodb_engine.contrib.MongoDBManager

   .. method:: map_reduce

      See :meth:`django_mongodb_engine.contrib.mapreduce.MapReduceMixin.map_reduce`


MapReduce Support for Django Models
-----------------------------------
.. autoclass:: django_mongodb_engine.contrib.mapreduce.MapReduceMixin
   :members:

.. autoclass:: django_mongodb_engine.contrib.mapreduce.MapReduceResult
   :members:
