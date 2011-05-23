Changelog
=========

.. currentmodule:: djangotoolbox.fields

Version 0.4
-----------
* :doc:`GridFS storage backend </topics/gridfs>`
* Fulltext search
* Query logging support
* Support for sparse indexes (see :doc:`/reference/model-options`)
* Database settings specific to MongoDB were moved into the ``OPTIONS`` dict.
  (see :doc:`/reference/settings`)
  Furthermore, the `SAFE_INSERTS` and `WAIT_FOR_SLAVES` flags are now deprecated
  in favor of the new ``OPERATIONS`` setting (see :ref:`operations-setting`)
* Added the :ref:`tellsiteid command <troubleshooting/SITE_ID>`
* Defined a stable :ref:`lower-level database API <lowerlevel/pymongo>`
* Numerous bug fixes, new tests, code improvements and deprecations

Version 0.3
-----------
* *OR* query support
* Support for :class:`~django.db.models.DateTimeField` and friends
* Support for atomic updates using F_
* :class:`EmbeddedModelField` has been `merged into djangotoolbox`_.
  For legacy data records in your setup, you can use the ``LegacyEmbeddedModelField``.
* Support for :ref:`raw queries and raw updates <lowerlevel/raw-queries-and-updates>`

.. * Added a flag to enable :ref:`model-referencing`

Version 0.2
-----------
* :doc:`Aggregation support </topics/aggregations>`
* :doc:`Map/Reduce support </topics/mapreduce>`
* :class:`ListField`, :class:`SetListField`, :class:`DictField` and
  :class:`GenericField` have been `merged into djangotoolbox`_
* Added an :class:`EmbeddedModelField` to store arbitrary model instances as
  MongoDB embedded objects/subobjects.
* Internal Refactorings

.. * Support for queries and updates on embedded models (see :ref:`embedded-object-queries`)

.. _merged into djangotoolbox: https://bitbucket.org/wkornewald/djangotoolbox/src/tip/djangotoolbox/fields.py
.. _F: http://docs.djangoproject.com/en/dev/topics/db/queries/#query-expressions
