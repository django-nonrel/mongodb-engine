Lower-Level Operations
======================

When you hit the limit of what's possible with Django's ORM, you can always go
down one abstraction layer to PyMongo_.

You can use :ref:`raw queries and updates <lowerlevel/raw-queries-and-updates>`
to update or query for model instances using raw Mongo queries, bypassing
Django's model query APIs.

If that isn't enough, you can skip the model layer entirely and operate on
:ref:`PyMongo-level objects <lowerlevel/pymongo>`.

.. warning::

   These APIs are available for MongoDB only, so using any of these features
   breaks portability to other non-relational databases (Google App Engine,
   Cassandra, Redis, ...). For the sake of portability you should try to avoid
   database-specific features whenever possible.


.. _lowerlevel/raw-queries-and-updates:

Raw Queries and Updates
-----------------------
.. currentmodule:: django_mongodb_engine.contrib

:class:`MongoDBManager` provides two methods, :meth:`~MongoDBManager.raw_query`
and :meth:`~MongoDBManager.raw_update`, that let you perform raw Mongo queries.

.. note::

   When writing raw queries, please keep in mind that no field name substitution
   will be done, meaning that you'll always have to use database-level names --
   e.g. `_id` instead of `id` or `foo_id` instead of `foo` for foreignkeys.

Raw Queries
...........
:meth:`~MongoDBManager.raw_query` takes one argument, the Mongo query to execute,
and returns a standard Django queryset -- which means that it also supports
indexing and further manipulation.

As an example, let's do some `Geo querying`_. ::

   from djangotoolbox.fields import EmbeddedModelField
   from django_mongodb_engine.contrib import MongoDBManager

   class Point(models.Model):
       latitude = models.FloatField()
       longtitude = models.FloatField()

   class Place(models.Model):
       ...
       location = EmbeddedModelField(Point)

       objects = MongoDBManager()

To find all places near to your current location, 42°N | π°E,
you can use this raw query::

   >>> here = {'latitude' : 42, 'longtitude' : 3.14}
   >>> Place.objects.raw_query({'location' : {'$near' : here}})

As stated above, :meth:`~MongoDBManager.raw_query` returns a standard Django
queryset, for which reason you can have even more fun with raw queries:

.. code-block:: pycon

   Limit the number of results to 10
   >>> Foo.objects.raw_query({'location' : ...})[:10]

   Keep track of most interesting places
   >>> Foo.objects.raw_query({'location' : ...) \
   ...            .update(interest=F('interest')+1)

   and whatnot.

Raw Updates
...........
:meth:`~MongoDBManager.raw_update` comes into play when Django MongoDB Engine's
atomic updates through ``$set`` and ``$inc`` (using F_)
are not powerful enough.

The first argument is the query which describes the subset of documents the
update should be executed against - as :class:`~django.db.models.Q` object or
Mongo query. The second argument is the update spec.

Consider this model::

   from django_mongodb_engine.contrib import MongoDBManager

   class FancyNumbers(models.Model):
       foo = models.IntegerField()

       objects = MongoDBManager()

Let's do some of those super-cool MongoDB in-place bitwise operations. ::

   FancyNumbers.objects.raw_update({}, {'$bit' : {'foo' : {'or' : 42}}})

That bitwise-ORs every `foo` of all documents in the database with 42.

To run that update against a subset of the documents, for example against any
whose `foo` is greater than π, use a non-empty filter condition::

   FancyNumbers.objects.raw_update(Q(foo__gt=3.14), {'$bit' : ...})
   # or
   FancyNumbers.objects.raw_update({'foo' : {'$gt' : 3.14}}, {'$bit' : ...})

.. _lowerlevel/pymongo:

PyMongo-level
-------------
:attr:`django.db.connections` is a dictionary-like object that holds all
database connections -- that is, for MongoDB databases,
:class:`django_mongodb_engine.base.DatabaseWrapper` instances.

These instances can be used to get the PyMongo-level :class:`~pymongo.Connection`,
:class:`~pymongo.database.Database` and :class:`~pymongo.collection.Collection`
objects.

For example, to execute a :meth:`~pymongo.collection.Collection.find_and_modify`
command, you could use code similar to this::

   from django.db import connections
   database_wrapper = connections['my_db_alias']
   eggs_collection = database_wrapper.get_collection('eggs')
   eggs_collection.find_and_modify(...)

.. _PyMongo: http://api.mongodb.org/python/current/
.. _Geo querying: http://docs.mongodb.org/manual/core/geospatial-indexes/
.. _F: https://docs.djangoproject.com/en/dev/topics/db/queries/#query-expressions
