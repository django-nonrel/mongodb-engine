Full List of MongoDB-specific Settings
======================================

Django MongoDB Engine provides a way to specify settings specific to MongoDB.

`Similar to Django's built-in backends`_, these optional settings can be specified
in ``OPTIONS`` dictionary in your ``DATABASES`` configuration.

All of these settings directly mirror PyMongo settings.
In fact, all Django MongoDB Engine does is lower-casing the names before passing
the flags to :class:`pymongo.Connection`. 
For a list of possible options head over to the `PyMongo documentation on connection options`_.

.. _operations-setting:

Setting Consistency Requirements for Database Operations
--------------------------------------------------------
Use the ``OPERATIONS`` dict to specify extra flags passed to
:meth:`pymongo.Collection.save`, :meth:`pymongo.Collection.update` or
:meth:`pymongo.Collection.remove`::

   'OPTIONS' : {
      ...
      'OPERATIONS' : {'w' : 3} # implies safe=True
   }

This passes ``safe=True, w=3`` as keyword arguments to each of
:meth:`~pymongo.Collection.save`, :meth:`~pymongo.Collection.update` and
:meth:`~pymongo.Collection.remove`.

Get a more fine-grained setup by introducing another layer to this dict::

   'OPTIONS' : {
      ...
      'OPERATIONS' : {
         'save' : {'safe' : True},
         'update' : {},
         'delete' : {'fsync' : True} # implies safe=True
   }


.. note::

   The operations showed above map to the **Django** operations `save`, `update`
   and `delete` (**not** to MongoDB operations). This is because Django abstracts
   "`insert vs. update`" into `save`.

.. _Similar to Django's built-in backends: 
   http://docs.djangoproject.com/en/dev/ref/settings/#std:setting-OPTIONS
.. _PyMongo documentation on connection options: http://api.mongodb.org/python/1.9%2B/api/pymongo/connection.html
