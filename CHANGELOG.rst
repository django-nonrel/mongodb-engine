Changelog
=========

.. currentmodule:: djangotoolbox.fields

Version 0.5.2 (Jun 19, 2015)
-----------------
* Add support for Replica Sets (Thanks @r4fek)
* Make safe writes the default (Thanks @markunsworth)


Version 0.5.1 (Nov 2013)
-----------------
* Fixed packaging issues


Version 0.5 (Nov 2013)
-----------------
Major changes
~~~~~~~~~~~~~
* Added support for Django 1.4-1.6, requires djangotoolbox >= 1.6.0
* PyPy support
* MongoDB 2.0 support
* We're now on Travis_
* New custom primary key behavior (to be documented)
* New ``MongoMeta.indexes`` system (see :doc:`/reference/model-options`),
  deprecation of ``MongoMeta.{index_together,descending_indexes,sparse_indexes}``

Minor changes/fixes
~~~~~~~~~~~~~~~~~~~
* Support for MongoDB :meth:`~django_mongodb_engine.contrib.MongoDBManager.distinct` queries
* Support for reversed-``$natural`` ordering using :meth:`~django.db.query.QuerySet.reverse`
* Dropped ``LegacyEmbeddedModelField``
* ``url()`` support for the :doc:`GridFS Storage <topics/gridfs>`
* Deprecation of ``A()`` queries
* Deprecation of the ``GridFSField.versioning`` feature
* Numerous query generator fixes
* Fixed ``DecimalField`` values sorting
* Other bug fixes, cleanup, new tests etc.


Version 0.4 (May 2011)
----------------------
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


Version 0.3 (Jan 2011)
----------------------
* *OR* query support
* Support for :class:`~django.db.models.DateTimeField` and friends
* Support for atomic updates using F_
* :class:`EmbeddedModelField` has been `merged into djangotoolbox`_.
  For legacy data records in your setup, you can use the ``LegacyEmbeddedModelField``.
* Support for :ref:`raw queries and raw updates <lowerlevel/raw-queries-and-updates>`

.. * Added a flag to enable :ref:`model-referencing`


Version 0.2 (Oct 2010)
----------------------
* :doc:`Aggregation support </topics/aggregations>`
* :doc:`Map/Reduce support </topics/mapreduce>`
* :class:`ListField`, :class:`SetListField`, :class:`DictField` and
  :class:`GenericField` have been `merged into djangotoolbox`_
* Added an :class:`EmbeddedModelField` to store arbitrary model instances as
  MongoDB embedded objects/subobjects.
* Internal Refactorings

.. * Support for queries and updates on embedded models (see :ref:`embedded-object-queries`)

.. _merged into djangotoolbox: https://github.com/django-nonrel/djangotoolbox/blob/master/djangotoolbox/fields.py
.. _F: http://docs.djangoproject.com/en/dev/topics/db/queries/#query-expressions
.. _Travis: http://travis-ci.org/django-nonrel/mongodb-engine
