Settings
========

.. TODO fix highlighting

Client Settings
-------------------
Additional flags may be passed to :class:`pymongo.MongoClient` using the
``OPTIONS`` dictionary::

   DATABASES = {
       'default' : {
           'ENGINE' : 'django_mongodb_engine',
           'NAME' : 'my_database',
           ...
           'OPTIONS' : {
               'socketTimeoutMS' : 500,
               ...
           }
       }
   }

All of these settings directly mirror PyMongo settings.  In fact, all Django
MongoDB Engine does is lower-casing the names before passing the flags to
:class:`~pymongo.MongoClient`.  For a list of possible options head over to the
`PyMongo documentation on client options`_.

.. _operations-setting:

Acknowledged Operations
-----------------------
Use the ``OPERATIONS`` dict to specify extra flags passed to
:meth:`Collection.save <pymongo.collection.Collection.save>`,
:meth:`~pymongo.collection.Collection.update` or
:meth:`~pymongo.collection.Collection.remove` (and thus included in the write concern):

.. code-block:: python

   'OPTIONS' : {
       'OPERATIONS' : {'w' : 3},
       ...
   }



Get a more fine-grained setup by introducing another layer to this dict:

.. code-block:: python

   'OPTIONS' : {
       'OPERATIONS' : {
           'save' : {'w' : 3},
           'update' : {},
           'delete' : {'j' : True}
       },
       ...
   }

.. note::

   This operations map to the **Django** operations `save`, `update` and `delete`
   (**not** to MongoDB operations). This is because Django abstracts
   "`insert vs. update`" into `save`.


A full list of write concern flags may be found in the
`MongoDB documentation <http://docs.mongodb.org/manual/core/write-concern/>`_.

.. _Similar to Django's built-in backends: 
   http://docs.djangoproject.com/en/dev/ref/settings/#std:setting-OPTIONS
.. _PyMongo documentation on client options:
   http://api.mongodb.org/python/current/api/pymongo/mongo_client.html
