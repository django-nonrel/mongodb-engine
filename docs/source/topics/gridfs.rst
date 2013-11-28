GridFS
======

MongoDB's built-in distributed file system, GridFS_, can be used in Django
applications in two different ways.

In most cases, you should use the GridFS :ref:`storage backend <gridfs/storage>`
provided by Django MongoDB Engine.

.. _gridfs/storage:

Storage
-------
:class:`~django_mongodb_engine.storage.GridFSStorage` is a `Django storage`_
that stores files in GridFS. That means it can be used with whatever component
makes use of storages -- most importantly,
:class:`~django.db.models.fields.files.FileField`.

It uses a special collection for storing files, by default named "storage". ::

   from django_mongodb_engine.storage import GridFSStorage

   gridfs = GridFSStorage()
   uploads = GridFSStorage(location='/uploads')

.. warning::

   To serve files out of GridFS, use tools like
   `nginx-gridfs <https://github.com/mdirolf/nginx-gridfs>`_.
   **Never** serve files through Django in production!


Model Field
-----------
(You should probably be using the :ref:`GridFS storage backend <gridfs/storage>`.)

Use :class:`~django_mongodb_engine.fields.GridFSField` to store "nameless" blobs
besides documents that would normally go into the document itself.

All that's kept in the document is a reference (an ObjectId) to the GridFS blobs
which are retrieved on demand.

Assuming you want to store a 10MiB blob "in" each document, this is what you
*shouldn't* do::

   # DON'T DO THIS
   class Bad(models.Model):
      blob = models.TextField()

   # NEITHER THIS
   class EventWorse(models.Model):
       blob = models.CharField(max_length=10*1024*1024)

Instead, use :class:`~django_mongodb_engine.fields.GridFSField`::

   class Better(models.Model):
       blob = GridFSField()

A GridFSField may be fed with anything that PyMongo can handle, that is,
(preferably) file-like objects and strings.

You'll always get a :class:`~gridfs.grid_file.GridOut` for documents from the
database. ::

   >>> doc = Better()

   GridFSField takes file-likes (and strings)...
   >>> doc.blob = file_like
   >>> doc.save()

    ... and always returns GridOuts.
   >>> samedoc = Better.objects.get(...)
   >>> samedoc.blob
   <GridOut object at 0xfoobar>

.. _GridFS: http://docs.mongodb.org/manual/core/gridfs/
.. _Django storage: https://docs.djangoproject.com/en/dev/topics/files/#file-storage
