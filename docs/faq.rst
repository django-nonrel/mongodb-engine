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
the ``django.db.backends`` logger, for example like this::

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
