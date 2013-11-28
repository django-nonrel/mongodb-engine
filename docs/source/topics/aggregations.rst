Aggregations
============

Django has `out-of-the-box support for aggregation`__.
The following aggregations are currently supported by Django MongoDB Engine:

* :class:`~django.db.models.Count`
* :class:`~django.db.models.Avg`
* :class:`~django.db.models.Min`
* :class:`~django.db.models.Max`
* :class:`~django.db.models.Sum`

MongoDB's group_ command is used to perform aggregations using generated
Javascript code that implements the aggregation functions.

While being more flexible than :doc:`mapreduce`, a ``group`` command can not be
processed in parallel, for which reason you should prefer Map/Reduce to process
big data sets.

.. warning::

   Needless to say, you shouldn't use these aggregations on a regular basis
   (i.e. in your views or business logic) but regard them as a powerful tool for
   one-time operations.

.. _group: http://docs.mongodb.org/manual/reference/command/group/#dbcmd.group
.. __: https://docs.djangoproject.com/en/dev/topics/db/aggregation/
