Troubleshooting
===============

This page is going to be a collection of common issues Django MongoDB Engine
users faced. Please help grow this collection --
:doc:`tell us about your troubles <meta/contributing>`!


.. _troubleshooting/SITE_ID:

``SITE_ID`` issues
------------------
.. code-block:: none

   AutoField (default primary key) values must be strings representing an ObjectId on MongoDB (got u'1' instead). Please make sure your SITE_ID contains a valid ObjectId string.

This means that your ``SITE_ID`` setting (`What's SITE_ID?!`_) is incorrect --
it is set to "1" but the site object that has automatically been created has an
ObjectId primary key.

If you add ``'django_mongodb_engine'`` to your list of ``INSTALLED_APPS``, you
can use the ``tellsiteid`` command to get the default site's ObjectId and update
your ``SITE_ID`` setting accordingly:

.. code-block:: none

   $ ./manage.py tellsiteid
   The default site's ID is u'deafbeefdeadbeef00000000'. To use the sites framework, add this line to settings.py:
   SITE_ID=u'deafbeefdeadbeef00000000'

.. _What's SITE_ID?!: http://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SITE_ID
