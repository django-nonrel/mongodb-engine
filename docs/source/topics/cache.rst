Caching
=======

.. note::

   This document assumes that you're already familiar with
   `Django's caching framework`_ (database caching in particular).

`Django MongoDB Cache`_ is a Django database cache backend similar to the one
built into Django (which only works with SQL databases).

Cache entries are structured like this:

.. code-block:: js

   {
     "_id" : <your key>,
     "v" : <your value>,
     "e" : <expiration timestamp>
   }

Thanks to MongoDB's ``_id`` lookups being very fast, MongoDB caching may be used
as a drop-in replacement for "real" cache systems such as Memcached in many cases.
(Memcached is still way faster and does a better caching job in general, but the
performance you get out of MongoDB should be enough for most mid-sized Web sites.)

Installation
------------
.. code-block:: bash

   git clone https://github.com/django-nonrel/mongodb-cache
   cd mongodb-cache
   python setup.py install

Setup
-----
Please follow the instructions in the `Django db cache setup docs`_ for details
on how to configure a database cache. Skip the ``createcachetable`` step since
there's no need to create databases in MongoDB.  Also, instead of the default db
cache backend name, use ``"django_mongodb_cache.MongoDBCache"`` as ``BACKEND``::

   CACHES = {
       'default' : {
           'BACKEND' : 'django_mongodb_cache.MongoDBCache',
           'LOCATION' : 'my_cache_collection'
       }
   }

Django MongoDB Cache will also honor all optional settings the default database
cache backend takes care of (``TIMEOUT``, ``OPTIONS``, etc).

.. _Django's caching framework: https://docs.djangoproject.com/en/dev/topics/cache/
.. _Django MongoDB Cache: https://github.com/django-nonrel/mongodb-cache
.. _Django db cache setup docs: https://docs.djangoproject.com/en/dev/topics/cache/#database-caching
