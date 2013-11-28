Map/Reduce
==========

Map/Reduce, originally invented at Google, is a simple but powerful technology
to efficiently process big amounts of data in parallel.

For this, your processing logic must be split into two phases, the *map* and the
*reduce* phase.

The *map phase* takes all the input you'd like to process (in terms of MongoDB,
this input are your *documents*) and emits one or more *key-value pairs* for
each data record (it "maps" records to key-value pairs).

The *reduce phase* "reduces" that set of key-value pairs into a single value.

This document explains how to use `MongoDB's Map/Reduce functionality`_
with Django models.

.. warning::

   MongoDB's Map/Reduce is designed for one-time operations, i.e. it's *not*
   intended to be used in code that is executed on a regular basis
   (views, business logic, ...).

.. currentmodule:: django_mongodb_engine.contrib

How to Use It
-------------
Map/Reduce support for Django models is provided through Django MongoDB Engine's
:class:`custom Manager <MongoDBManager>`
(:class:`What is a manager? <django.db.models.Manager>`). ::

   from django_mongodb_engine.contrib import MongoDBManager

   class MapReduceableModel(models.Model):
       ...
       objects = MongoDBManager()

The :class:`MongoDBManager` provides a :meth:`~MongoDBManager.map_reduce` method
that has the same API as PyMongo's :meth:`~pymongo.collection.Collection.map_reduce`
method (with the one exception that it adds a `drop_collection` option). ::

   >>> MapReduceableModel.objects.map_reduce(mapfunc, reducefunc, output_collection, ...)

For very small result sets, you can also use in-memory Map/Reduce::

   >>> MapReducableModel.objects.inline_map_reduce(mapfunc, reducefunc, ...)

It's also possible to run Map/Reduce against a subset of documents in the database::

   >>> MapReduceableModel.objects.filter(...).map_reduce(...)

Both the map and the reduce function are written in Javascript.

:meth:`~MongoDBManager.map_reduce` returns an iterator yielding
:class:`MapReduceResult` objects.

Special Reduce Function Rules
-----------------------------
A sane reduce function must be both associative and commutative -- that is,
in terms of MongoDB, the following conditions must hold true::

   # Value order does not matter:
   reduce(k, [A, B]) == reduce(k, [B, A])
   # Values may itself be results of other reduce operations:
   reduce(k, [reduce(k, ...)]) == reduce(k, ...)

This is because in order to be able to process in parallel, the reduce phase
is split into several sub-phases, reducing parts of the map output and eventually
merging them together into one grand total.

Example
-------
(See also :ref:`the example in the tutorial <tutorial/mapreduce>` and
`Wikipedia <http://en.wikipedia.org/wiki/MapReduce>`_, from which I stole the
idea for the example beneath.)

As an example, we'll count the number of occurrences of each word in a bunch of
articles. Our models could look somewhat like this:

.. literalinclude:: ../code/mapreduce/mr/models.py
   :start-after: models
   :end-before: class Author

Our map function emits a ``(word, 1)`` pair for each word in an article's text
(In the map function, `this` always refers to the current document).

.. code-block:: js

   function() {
     this.text.split(' ').forEach(
       function(word) { emit(word, 1) }
     )
   }

For an input text of "Django is named after Django Reinhardt", this would emit
the following key-value pairs::

   Django : 1
   is : 1
   named : 1
   after : 1
   Django : 1
   Reinhardt : 1

This pairs are now combined in such way that no key duplicates are left. ::

   is : [1]
   named : [1]
   after : [1]
   Django : [1, 1]
   Reinhardt : [1]

To further process these pairs, we let our reduce function sum up all
occurrences of each word

.. code-block:: js

   function reduce(key, values) {
     return values.length; /* == sum(values) */
   }

so that the final result is a list of key-"sum"-pairs::

   is : 1
   named : 1
   after : 1
   Django : 2
   Reinhardt : 1

Show Me the Codes
-----------------
Here's a full example, using the models and functions described above, on how to
use Django MongoDB Engine's Map/Reduce API.

.. literalinclude:: ../code/mapreduce/mr/models.py

.. literalinclude:: ../code/mapreduce/mr/tests.py
   :end-before: __test__

.. literalinclude:: ../code/mapreduce/mr/tests.py
   :start-after: mr
   :end-before: """


.. _MongoDB's Map/Reduce functionality: http://docs.mongodb.org/manual/core/map-reduce/
