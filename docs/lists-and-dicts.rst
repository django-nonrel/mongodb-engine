Storing Python Lists and Dicts
==============================

Using :class:`ListField` and :class:`DictField`, you can store *arbitrary* Python
lists, dicts and sets in MongoDB.

.. class:: ListField
.. class:: SetField

   Example::

      from djangotoolbox.fields import ListField, SetField

      def optional_ordering(n):
          """ Optional ordering function (sorts reversed) """
          return -n

      class Post(models.Model):
          title = models.CharField()
          tags = SetField(default=set())
          ratings = ListField(models.IntegerField(), ordering=optional_ordering)

   A ``Post``'s ``tags`` attribute now is a standard Python list::

      >>> post_about_turtles = Post.objects.create(title='I Like Turtles',
      ...                                          tags=['animals', 'food'])
      >>> post_about_turtles.tags.remove('food') # nobody would eat animals, right?
      >>> post_about_turtles.save()
      >>> Post.objects.get().tags
      set(['animals']) # see how the list got a set

   If you pass a field instance as argument, items of the list or dict will be
   converted into a data type compatible to this field::

      >>> post_about_turtles.ratings.extend(['1', 3.14])
      >>> post_about_turtles.save()
      >>> Post.objects.get().ratings
      [3, 1] # reverse-ordering function, remember?

   Let's have a look at the MongoDB data set.

   .. code-block:: js

      /* > db.docs_post.findOne() */
      {
          "_id" : ObjectId("4cee6e62e4721c6508000000"),
          "ratings" : [
              1,
              3
          ],
          "tags" : [
              "animal"
          ],
          "title" : "I Like Turtles"
      }

.. class:: DictField

   behaves similar::

      from djangotoolbox.fields import DictField

      class MyMotherWentShopping(models.Model):
          and_she_bought = DictField()

   ::

      >>> my_mother_went_shopping = MyMotherWentShopping()
      >>> my_mother_went_shopping.and_she_bought = {
      ...     'eggs' : 3,
      ...     'bread' : 'two loafs',
      ...     'tofu' : (None, ['because I hate tofu'])
      ... }
      >>> my_mother_went_shopping.save()
      >>> MyMotherWentShopping.objects.get().and_she_bought
      {u'bread': u'two loafs', u'eggs': 3, u'tofu': [None, [u'because I hate tofu']]}

   As you can see, the tuple of the *tofu* item ends up being a list when fetched
   from the database. That's because MongoDB has no tuples and nobody told Django
   to convert it to a tuple, so it's still a list.
