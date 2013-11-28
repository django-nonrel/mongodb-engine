Embedded Models
===============

Django MongoDB Engine supports `MongoDB's subobjects`_ which can be used
to embed an object into another.

Using :ref:`topics/listfield` and :ref:`topics/dictfield` it's already possible
to embed objects (:class:`dicts <dict>`) of arbitrary shape.

However, EmbeddedModelField (described beneath) is a much more comfortable tool
for many use cases, ensuring the data you store actually matches the structure
and types you want it to be in.

The Basics
----------
Let's consider this example::

   from djangotoolbox.fields import EmbeddedModelField

   class Customer(models.Model):
       name = models.CharField(...)
       address = EmbeddedModelField('Address')
       ...

   class Address(models.Model):
       ...
       city = models.CharField(...)

The API feels very natural and is similar to that of Django's relation fields. ::

   >>> Customer(name='Bob', address=Address(city='New York', ...), ...).save()
   >>> bob = Customer.objects.get(...)
   >>> bob.address
   <Address: Address object>
   >>> bob.address.city
   'New York'

Represented in BSON, Bob's structure looks like this:

.. code-block:: js

   {
     "_id": ObjectId(...),
     "name": "Bob",
     "address": {
       ...
       "city": "New York"
     },
     ...
   }

While such "flat" embedding is useful if you want to bundle multiple related
fields into one common namespace -- for instance, in the example above we
bundled all information about a customers' address into the `address` namespace
-- there's a much more common usecase for embedded objects: one-to-many relations.

.. _topics/list-of-subobjects:

Lists of Subobjects (One-to-Many Relations)
-------------------------------------------
Often, lists of subobjects are superior to relations (in terms of simplicity and
performance) for modeling one-to-many relationships between models.

Consider this elegant way to implement the Post ⇔ Comments relationship::

   from djangotoolbox.fields import ListField, EmbeddedModelField

   class Post(models.Model):
       ...
       comments = ListField(EmbeddedModelField('Comment'))

   class Comment(models.Model):
       text = models.TextField()

Embedded objects are represented as subobjects on MongoDB::

  >>> comments = [Comment(text='foo'), Comment(text='bar')]
  >>> Post(comments=comments, ...).save()
  >>> Post.objects.get(...).comments
  [<Comment: Comment object>, <Comment: Comment object>]

.. code-block:: js

   {
     "_id": ObjectId(...),
     ...
     "comments" : [
       {"text": "foo", },
       {"text": "bar"}
     ]
   }

Generic Embedding
-----------------
Similar to Django's `generic relations`_, it's possible to embed objects of any
type (sometimes referred to as "polymorphic" relationships). This works by
adding the model's name and module to each subobject, accompanying the actual
data with type information:

.. code-block:: js

   {
     "_id" : ObjectId(...),
     "stuff" : [
       {"foo" : 42, "_module" : "demoapp.models", "_model" : "FooModel"},
       {"bar" : "spam", "_module" : "demoapp.models", "_model" : "FooModel"}
     ]
   }

As you can see, generic embedded models add a lot of overhead that bloats up
your data records. If you want to use them anyway, here's how you'd do it::

   class Container(models.Model):
       stuff = ListField(EmbeddedModelField())

   class FooModel(models.Model):
       foo = models.IntegerField()

   class BarModel(models.Model):
       bar = models.CharField(max_length=255)

::

   Container.objects.create(
       stuff=[FooModel(foo=42), BarModel(bar='spam')]
   )

.. _MongoDB's subobjects: http://docs.mongodb.org/manual/core/data-model-design/
.. _generic relations: https://docs.djangoproject.com/en/dev/ref/contrib/contenttypes/
