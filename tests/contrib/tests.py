from __future__ import with_statement

from functools import partial

from django.db.models import Q
from django.db.utils import DatabaseError

from django_mongodb_engine.contrib import MapReduceResult

from models import *
from utils import TestCase, get_collection, skip


class MapReduceTests(TestCase):

    def test_map_reduce(self, inline=False):
        mapfunc = """
            function map() {
                for(i=0; i<this.n; ++i) {
                    emit(this._id, this.m)
                }
            }
        """

        reducefunc = """
            function reduce(key, values) {
                var res = 0
                values.forEach(function(x) { res += x})
                return res
            }
        """

        if inline:
            map_reduce = MapReduceModel.objects.inline_map_reduce
        else:
            map_reduce = partial(MapReduceModel.objects.map_reduce,
                                 out='m/r-out')
        map_reduce = partial(map_reduce, mapfunc, reducefunc)

        random_numbers = [
            (3, 4),
            (6, 19),
            (5, 8),
            (0, 20), # This instance won't be emitted by `map`.
            (2, 77),
            (300, 10),
        ]

        for n, m in random_numbers:
            MapReduceModel(n=n, m=m).save()

        # Test mapfunc + reducefunc.
        documents = map_reduce()
        documents = list(documents)
        self.assertEqual(len(documents), len(random_numbers) - 1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n * m for n, m in random_numbers))

        # Test MapReduceResult.
        obj = documents[0].model.objects.get(id=documents[0].key)
        self.assert_(isinstance(obj, MapReduceModel))
        self.assertEqual((obj.n, obj.m), random_numbers[0])
        self.assert_(obj.id)

        # Collection should not have been perished.
        if not inline:
            result_collection = get_collection('m/r-out')
            self.assertEqual(result_collection.count(),
                             len(random_numbers) - 1)

            # Test drop_collection.
            map_reduce(drop_collection=True).next()
            self.assertEqual(get_collection('m/r-out').count(), 0)

        # Test arbitrary kwargs.
        documents = list(map_reduce(limit=3))
        self.assertEqual(len(documents), 3)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n * m for n, m in random_numbers[:3]))

        # Test with .filter(...).
        qs = MapReduceModel.objects.filter(n__lt=300).filter(~Q(m__in=[4]))
        if inline:
            documents = qs.inline_map_reduce(mapfunc, reducefunc)
        else:
            documents = list(qs.map_reduce(mapfunc,
                                           reducefunc, out='m/r-out'))
        self.assertEqual(len(documents), len(random_numbers) - 2 - 1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n * m for n, m in random_numbers[1:-1]))

    def test_inline_map_reduce(self):
        self.test_map_reduce(inline=True)
        self.test_map_reduce_with_custom_primary_key(inline=True)

    def test_map_reduce_with_custom_primary_key(self, inline=False):
        mapfunc = """ function() { emit(this._id, null) } """
        reducefunc = """ function(key, values) { return null } """
        for pk, data in [
            ('foo', 'hello!'),
            ('bar', 'yo?'),
            ('blurg', 'wuzzup'),
        ]:
            MapReduceModelWithCustomPrimaryKey(
                primarykey=pk, data=data).save()

        if inline:
            somedoc = MapReduceModelWithCustomPrimaryKey.objects \
                            .inline_map_reduce(mapfunc, reducefunc)[0]
        else:
            somedoc = MapReduceModelWithCustomPrimaryKey.objects.map_reduce(
                            mapfunc, reducefunc, out='m/r-out').next()
        self.assertEqual(somedoc.key, 'bar') # Ordered by pk.
        self.assertEqual(somedoc.value, None)
        obj = somedoc.model.objects.get(pk=somedoc.key)
        self.assert_(not hasattr(obj, 'id') and not hasattr(obj, '_id'))
        self.assertEqual(obj, MapReduceModelWithCustomPrimaryKey(pk='bar',
                                                                 data='yo?'))


class RawQueryTests(TestCase):

    def setUp(self):
        for i in xrange(10):
            MapReduceModel.objects.create(n=i, m=i * 2)

    def test_raw_query(self):
        len(MapReduceModel.objects.raw_query({'n': {'$gt': 5}})) # 11
        self.assertEqual(
            list(MapReduceModel.objects.filter(n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n': {'$gt': 5}})))
        self.assertEqual(
            list(MapReduceModel.objects.filter(n__lt=9, n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n': {'$lt': 9}})
                    .filter(n__gt=5)))

        MapReduceModel.objects.raw_query({'n': {'$lt': 3}}).update(m=42)
        self.assertEqual(
            list(MapReduceModel.objects.raw_query({'n': {'$gt': 0}})
                    .filter(n__lt=3)),
            list(MapReduceModel.objects.all()[1:3]))
        self.assertEqual(
            list(MapReduceModel.objects.values_list('m')[:5]),
            [(42,), (42,), (42,), (6,), (8,)])

    def test_raw_update(self):
        from django.db.models import Q
        MapReduceModel.objects.raw_update(Q(n__lte=3), {'$set': {'n': -1}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [-1, -1, -1, -1, 4, 5, 6, 7, 8, 9])
        MapReduceModel.objects.raw_update({'n': -1}, {'$inc': {'n': 2}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [1, 1, 1, 1, 4, 5, 6, 7, 8, 9])


# TODO: Line breaks.
class FullTextTest(TestCase):

    def test_simple_fulltext(self):
        blog = Post(content="simple, full text.... search? test")
        blog.save()

        self.assertEqual(
            Post.objects.get(content="simple, full text.... search? test"),
            blog)
        self.assertEqual(
            Post.objects.get(content_tokenized="simple, search? test"),
            blog)

    def test_simple_fulltext_filter(self):
        Post(content="simple, fulltext search test").save()
        Post(content="hey, how's, it, going.").save()
        Post(content="this full text search... seems to work... "
                     "pretty? WELL").save()
        Post(content="I would like to use MongoDB for FULL "
                     "text search").save()

        self.assertEqual(
            len(Post.objects.filter(content_tokenized="full text")), 2)
        self.assertEqual(
            len(Post.objects.filter(content_tokenized="search")), 3)
        self.assertEqual(
            len(Post.objects.filter(content_tokenized="It-... GoiNg")), 1)

    def test_int_fulltext_lookup(self):
        Post(content="this full text search... seems to work... "
                     "pretty? WELL").save()
        Post(content="I would like to use MongoDB for FULL "
                     "text search").save()
        Post(content="just some TEXT without the f u l l  word").save()

        self.assertEqual(
            len(Post.objects.filter(content_tokenized__in="full text")), 3)

    def test_or_fulltext_queries(self):
        Post(content="Happy New Year Post.... Enjoy").save()
        Post(content="So, Django is amazing, we all know that but django and "
                     "mongodb is event better ;)").save()
        Post(content="Testing the full text django + mongodb "
                     "implementation").save()

        self.assertEqual(
            len(Post.objects.filter(
                Q(content_tokenized="django mongodb better?") |
                Q(content_tokenized="full text mongodb"))),
            2)

    @skip("Broken.")
    def test_and_fulltext_queries(self):
        Post(content="Happy New Year Post.... Enjoy").save()
        Post(content="So, Django is amazing, we all know that but django and "
                     "mongodb is event better ;)").save()
        post = Post(content="Testing the full text django + mongodb "
                            "implementation")
        post.save()

        self.assertEqual(
            Post.objects.get(
                Q(content_tokenized="django mongodb") &
                Q(content_tokenized="testing")).pk,
            post.pk)

    def test_for_wrong_lookups(self):
        # This is because full text queries run over a list of
        # tokenized values so djangotoolbox will complain.
        # We should find a workaround for this.
        # For example: Using the iexact lookup could be useful because
        # it could be passed to the tokenizer in order to support Case
        # Sensitive Case Insensitive queries.
        with self.assertRaises(DatabaseError):
            Post.objects.get(content_tokenized__iexact="django mongodb")
            Post.objects.get(content_tokenized__icontains="django mongodb")


class DistinctTests(TestCase):

    def test_distinct(self):
        for i in xrange(10):
            for j in xrange(i):
                MapReduceModel.objects.create(n=i, m=i * 2)

        self.assertEqual(MapReduceModel.objects.distinct('m'),
                         [2, 4, 6, 8, 10, 12, 14, 16, 18])

        self.assertEqual(MapReduceModel.objects.filter(n=6).distinct('m'), [12])
