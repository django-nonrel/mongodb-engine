========================================================
 django-mongodb-engine -- `MongoDB`_ Backend for Django
========================================================

.. _MongoDB: http://mongodb.org

*django-mongodb-engine* is a full-featured MongoDB backend for Django
including support for :doc:`Embedded Objects </embedded-objects>`,
:doc:`lists and dicts </lists-and-dicts>`, aggregations and
:ref:`Map/Reduce <mapreduce>`.


Quickstart
~~~~~~~~~~
Get the *latest* versions of `djangotoolbox`_, `Django-nonrel`_ and
django-mongodb-engine from GitHub::

   git clone git://github.com/django-mongodb-engine/mongodb-engine
   cd mongodb-engine && python setup.py install

Database setup is easy (see also: `Django database setup docs`_)::

   DATABASES = {
      'default' : {
         'ENGINE' : 'django_mongodb_engine',
         'NAME' : 'my_database',

         # optional:
         'HOST' : 'localhost',
         'PORT' : 27017,
         'SUPPORTS_TRANSACTIONS' : False
      }
   }

**That's it!** You can now go straight ahead developing your Django application
as you would do with any other database.

.. _Django database setup docs: http://docs.djangoproject.com/en/dev/ref/settings/#databases
.. _djangotoolbox: http://allbuttonspressed.com/#TODO
.. _Django-nonrel: http://allbuttonspressed.com/#TODO


This might be interesting, too:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   Embedded Objects Instead of JOINs <embedded-objects>
   Lists and Dicts Instead of JOINS <lists-and-dicts>
   cool-stuff
   faq
