Settings
========

.. TODO fix highlighting

Connection Settings
-------------------
Additional flags may be passed to :class:`pymongo.Connection` using the
``OPTIONS`` dictionary::

   DATABASES = {
       'default' : {
           'ENGINE' : 'django_mongodb_engine',
           'NAME' : 'my_database',
           ...
           'OPTIONS' : {
               'slave_okay' : True,
               'tz_aware' : True,
               'network_timeout' : 42,
               ...
           }
       }
   }

All of these settings directly mirror PyMongo settings.  In fact, all Django
MongoDB Engine does is lower-casing the names before passing the flags to
:class:`~pymongo.Connection`.  For a list of possible options head over to the
`PyMongo documentation on connection options`_.

.. _operations-setting:

Safe Operations (``getLastError``)
----------------------------------
Use the ``OPERATIONS`` dict to specify extra flags passed to
:meth:`Collection.save <pymongo.collection.Collection.save>`,
:meth:`~pymongo.collection.Collection.update` or
:meth:`~pymongo.collection.Collection.remove` (and thus to ``getLastError``):

.. code-block:: python

   'OPTIONS' : {
       'OPERATIONS' : {'w' : 3},
       ...
   }

Since any options to ``getLastError`` imply ``safe=True``,
this configuration passes ``safe=True, w=3`` as keyword arguments to each of
:meth:`~pymongo.collection.Collection.save`,
:meth:`~pymongo.collection.Collection.update` and
:meth:`~pymongo.collection.Collection.remove`.

Get a more fine-grained setup by introducing another layer to this dict:

.. code-block:: python

   'OPTIONS' : {
       'OPERATIONS' : {
           'save' : {'safe' : True},
           'update' : {},
           'delete' : {'fsync' : True}
       },
       ...
   }

.. note::

   This operations map to the **Django** operations `save`, `update` and `delete`
   (**not** to MongoDB operations). This is because Django abstracts
   "`insert vs. update`" into `save`.


A full list of ``getLastError`` flags may be found in the
`MongoDB documentation <http://www.mongodb.org/display/DOCS/getLastError+Command>`_.

.. _Similar to Django's built-in backends: 
   http://docs.djangoproject.com/en/dev/ref/settings/#std:setting-OPTIONS
.. _PyMongo documentation on connection options: 
   http://api.mongodb.org/python/current/api/pymongo/connection.html
