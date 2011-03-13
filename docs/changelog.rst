Changelog
=========

Version 0.4
-----------
* GridFS storage backend TODO docs
* Fulltext search support TODO docs
* :ref:`Query debugging support <query-debugging>`
* Database settings specific to MongoDB were moved into the ``OPTIONS`` dict.
  (see :ref:`settings`)
  Furthermore, the `SAFE_INSERTS` and `WAIT_FOR_SLAVES` flags are now deprecated
  in favor of the new ``OPERATIONS`` setting (see :ref:`operations-setting`)
* Numerous bug fixes, new tests, code improvements and deprecations

Version 0.3
-----------
* *OR* query support
* ``date``, ``time`` and ``datetime`` support
* Support for ``F``-updates
* ``EmbeddedModelField`` has been `merged into djangotoolbox`_.
  For legacy data records in your setup, you can use the ``LegacyEmbeddedModelField``.
* Support for :ref:`raw queries and raw updates <raw-queries-and-updates>`
* Added a flag to enable :ref:`model-referencing`

Version 0.2
-----------
* Django aggregation support
* :ref:`Map/Reduce support <mapreduce>`
* ``ListField``, ``SetListField``, ``DictField`` and ``GenericField`` have been
  `merged into djangotoolbox`_
* Added an ``EmbeddedModelField`` to store arbitrary model instances as
  MongoDB embedded objects/subobjects.
* Support for queries and updates on embedded models (see :ref:`embedded-object-queries`)
* Internal Refactorings

.. _merged into djangotoolbox: https://bitbucket.org/wkornewald/djangotoolbox/src/tip/djangotoolbox/fields.py
