Changelog
=========

Version 0.3
-----------
* *OR* query support
* ``date``, ``time`` and ``datetime`` support
* Support for ``F``-updates
* ``EmbeddedModelField`` has been `merged into djangotoolbox`_.
  For legacy data records in your setup, you can use the ``LegacyEmbeddedModelField``.
* Support for :ref:`raw queries and raw updates <raw-queries-and-updates>`
* :ref:`GridFS storage implementation <gridfs-storage>`
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
