Frequently Asked Questions
==========================

Does it support JOINs?
~~~~~~~~~~~~~~~~~~~~~~
No, because MongoDB doesn't, but have look at
:doc:`embedded-objects` and :doc:`lists-and-dicts`.

Does it support transactions?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
No, because MongoDB doesn't.

Can I do Raw Queries/Updates?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Yep! See :ref:`raw-queries-and-updates`.

How can I use Capped Collections?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
See :ref:`collection-options`.

.. _query-debugging:

Does it support query debugging?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Yep! Set ``DEBUG`` to :const:`True` in your :file:`settings.py` and
`configure <http://docs.djangoproject.com/en/dev/topics/logging/#configuring-logging>`_
the ``django.db.backends`` logger (example follows).

Please keep in mind that :ref:`Map/Reduce <mapreduce>` and aggregation queries
are not logged because they involve lots of JavaScript code (aggregations are
implemented with `group` internally).

::

   LOGGING = {
       'version' : 1,
       'formatters' : {'simple' : {'format': '%(levelname)s %(message)s'}},
       'handlers' : {
           'console' : {
               'level' : 'DEBUG',
               'class' : 'logging.StreamHandler',
               'formatter' : 'simple'
           }
       },
       'loggers' : {
           'django.db.backends' : {
               'level' : 'DEBUG',
               'handlers' : ['console']
           }
       }
   }
