Atomic Updates
==============

Django's support for updates_
(using the :meth:`~django.db.models.query.QuerySet.update` method)
can be used to run atomic updates against a single or multiple documents::

   Post.objects.filter(...).update(title='Everything is the same')

results in a :meth:`~pymongo.collection.Collection.update` query that uses the
atomic ``$set`` operator to update the `title` field::

   .update(..., {'$set': {'title': 'Everything is the same'}})

It's also possible to use `F()`_ objects which are
translated into ``$inc`` operations. For example, ::

   Post.objects.filter(...).update(visits=F('visits')+1)

is translated to::

   .update(..., {'$inc': {'visits': 1}})

.. _updates: https://docs.djangoproject.com/en/dev/topics/db/queries/#updating-multiple-objects-at-once
.. _F(): https://docs.djangoproject.com/en/dev/topics/db/queries/#filters-can-reference-fields-on-the-model
