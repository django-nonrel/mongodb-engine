Lists & Dicts
=============

Django MongoDB Engine provides two fields for storing arbitrary (BSON-compatible)
Python :class:`list` and :class:`dict` objects in Django model objects,
:ref:`ListField <topics/listfield>` and :ref:`DictField <topics/dictfield>`,
which can be used to store information that is not worth a separate model or
that should be queryable in efficient manner (using an index).

Both fields may optionally be provided with type information. That restricts
their usage to one single type but has the advantage of automatic type checks
and conversions.

.. _topics/listfield:

ListField
---------
Stores Python lists (or any other iterable), represented in BSON as arrays. ::

   from djangotoolbox.fields import ListField

   class Post(models.Model):
       ...
       tags = ListField()

::

   >>> Post(tags=['django', 'mongodb'], ...).save()
   >>> Post.objects.get(...).tags
   ['django', 'mongodb']

The typed variant automatically does type conversions according to the given type::

   class Post(models.Model):
       ...
       edited_on = ListField(models.DateTimeField())

::

   >>> post = Post(edited_on=['1010-10-10 10:10:10'])
   >>> post.save()
   >>> Post.objects.get(...).edited_on
   [datetime.datetime([1010, 10, 10, 10, 10, 10])]

As described :ref:`in the tutorial <tutorial/embedded-models>`, ListFields are
very useful when used together with :doc:`embedded-models` to store lists of
sub-entities to model 1-to-n relationships::

   from djangotoolbox.fields import EmbeddedModelField, ListField

   class Post(models.Model):
       ...
       comments = ListField(EmbeddedModelField('Comment'))

   class Comment(models.Model):
       ...
       text = models.TextField()

Please head over to the :doc:`embedded-models` topic for more about embedded models.

SetField
--------
Much like a :ref:`ListField <topics/listfield>` except that it's represented as
a :class:`set` on Python side (but stored as a list on MongoDB due to the lack
of a separate set type in BSON).

.. _topics/dictfield:

DictField
---------
Stores Python dicts (or any dict-like iterable), represented in BSON as subobjects. ::

   from djangotoolbox.fields import DictField

   class Image(models.Model):
       ...
       exif = DictField()

::

   >>> Image(exif=get_exif_data(...), ...).save()
   >>> Image.objects.get(...).exif
   {u'camera_model' : 'Spamcams 4242', 'exposure_time' : 0.3, ...}

The typed variant automatically does type conversion on values. (Not on keys
as the are required to be strings on MongoDB.) ::

   class Poll(models.Model):
       ...
       votes = DictField(models.IntegerField())

::

   >>> Poll(votes={'bob' : 3.14, 'alice' : '42'}, ...).save()
   >>> Poll.objects.get(...).votes
   {u'bob' : 3, u'alice' : 42}

DictFields are useful mainly for storing objects of varying shape, i.e. objects
whose structure is unknow at coding time.  If all your objects have the same
structure, you should consider using :doc:`embedded-models`.
