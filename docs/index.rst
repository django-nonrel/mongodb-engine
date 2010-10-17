========================================================
 django-mongodb-engine -- `MongoDB`_ Backend for Django
========================================================

.. _MongoDB: http://mongodb.org

Setup
-----

No special setup needed, just set ``django_mongodb_engine`` as your database
``ENGINE``, pick a ``NAME`` and, if needed, change ``HOST`` and ``PORT`` to match
your needs. Additionally, you should provide the ``SUPPORRTS_TRANSACTIONS``
option in your ``DATABASES`` settings::

   DATABASES = {
      'default' : {
         'ENGINE' : 'django_mongodb_engine',
         'NAME' : 'myproject_db',
         'SUPPORTS_TRANSACTIONS' : False
      }
   }


Questions?
----------
Does it support transcations?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
No, because MongoDB doesn't.

Does it support JOINs?
~~~~~~~~~~~~~~~~~~~~~~
No, because MongoDB doesn't, but

* you can use djangotoolbox' ``DictField``, ``ListField`` and ``SetField`` to
  store Python lists, sets and dictionaries
* you can embed model instances using :class:`django_mongodb_engine.fields.EmbeddedModelField`
* you can combine those two


User Docs
---------
.. toctree::
   :maxdepth: 2

   fields
   contrib

Internals
---------
.. toctree::
   :maxdepth: 2

   internals/index
