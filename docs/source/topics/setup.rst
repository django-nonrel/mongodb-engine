Setup
=====

This page explains how to install and configure a Django/MongoDB setup.

Installation
------------
Django MongoDB Engine depends on

* Django-nonrel_, a fork of Django that adds support for non-relational databases
* djangotoolbox_, a bunch of utilities for non-relational Django applications and backends

It's highly recommended (although not required) to use a virtualenv_ for your
project to not mess up other Django setups.

virtualenv
..........
If not already installed, grab a copy from the Cheeseshop::

   pip install virtualenv

To set up a virtual environment for your project, use ::

   virtualenv myproject

To join the environment, use (in Bash)::

   source myproject/bin/activate

Django-nonrel
.............
::

   pip install git+https://github.com/django-nonrel/django@nonrel-1.5

djangotoolbox
.............
::

   pip install git+https://github.com/django-nonrel/djangotoolbox

Django MongoDB Engine
.....................
You should use the latest Git revision. ::

   pip install git+https://github.com/django-nonrel/mongodb-engine


Configuration
-------------
Database setup is easy (see also the `Django database setup docs`_)::

   DATABASES = {
      'default' : {
         'ENGINE' : 'django_mongodb_engine',
         'NAME' : 'my_database'
      }
   }

Django MongoDB Engine also takes into account the ``HOST``, ``PORT``, ``USER``,
``PASSWORD`` and ``OPTIONS`` settings.

Possible values of ``OPTIONS`` are described in the
:doc:`settings reference </reference/settings>`.

Done!
-----
That's it! You can now go straight ahead developing your Django application as
you would do with any other database.


.. _virtualenv: http://www.virtualenv.org/
.. _Django database setup docs: https://docs.djangoproject.com/en/dev/ref/settings/#databases
.. _djangotoolbox: https://github.com/django-nonrel/djangotoolbox
.. _Django-nonrel: http://django-nonrel.org/
