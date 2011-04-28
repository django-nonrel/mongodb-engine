from django.db.models import Q
from django.db.utils import DatabaseError
from django_mongodb_engine.contrib import MapReduceResult

from .utils import TestCase, get_collection
from .models import *

class MapReduceTests(TestCase):
    def test_map_reduce(self):
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

        random_numbers = [
            (3, 4),
            (6, 19),
            (5, 8),
            (0, 20), # this instance won't be emitted by `map`
            (2, 77),
            (300, 10)
        ]

        for n, m in random_numbers:
            MapReduceModel(n=n, m=m).save()

        # Test mapfunc + reducefunc
        documents = MapReduceModel.objects.map_reduce(mapfunc, reducefunc,
                                                      out='m/r-out')
        documents = list(documents)
        self.assertEqual(len(documents), len(random_numbers)-1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n*m for n, m in random_numbers))

        # Test MapReduceResult
        obj = documents[0].model.objects.get(id=documents[0].key)
        self.assert_(isinstance(obj, MapReduceModel))
        self.assertEqual((obj.n, obj.m), random_numbers[0])
        self.assert_(obj.id)

        # Collection should not have been perished
        result_collection = get_collection('m/r-out')
        self.assertEqual(result_collection.count(), len(random_numbers)-1)
        result_collection.drop()

        # Test drop_collection
        MapReduceModel.objects.map_reduce(mapfunc, reducefunc, out='m/r-out')
        self.assertEqual(get_collection('m/r-out').count(), 0)

        # Test arbitrary kwargs
        documents = MapReduceModel.objects.map_reduce(mapfunc, reducefunc,
                                                      out='m/r-out', limit=3)
        documents = list(documents)
        self.assertEqual(len(documents), 3)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n*m for n, m in random_numbers[:3]))

        # Test with .filter(...)
        qs = MapReduceModel.objects.filter(n__lt=300).filter(~Q(m__in=[4]))
        documents = list(qs.map_reduce(mapfunc, reducefunc, out='m/r-out'))
        self.assertEqual(len(documents), len(random_numbers)-2-1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n*m for n, m in random_numbers[1:-1]))

    def test_map_reduce_with_custom_primary_key(self):
        mapfunc = """ function() { emit(this._id, null) } """
        reducefunc = """ function(key, values) { return null } """
        for pk, data in [
            ('foo', 'hello!'),
            ('bar', 'yo?'),
            ('blurg', 'wuzzup')
        ]:
            MapReduceModelWithCustomPrimaryKey(primarykey=pk, data=data).save()

        documents = MapReduceModelWithCustomPrimaryKey.objects.map_reduce(
            mapfunc, reducefunc, out='m/r-out')
        somedoc = documents.next()
        self.assertEqual(somedoc.key, 'bar') # ordered by pk
        self.assertEqual(somedoc.value, None)
        obj = somedoc.model.objects.get(pk=somedoc.key)
        self.assert_(not hasattr(obj, 'id') and not hasattr(obj, '_id'))
        self.assertEqual(obj, MapReduceModelWithCustomPrimaryKey(pk='bar', data='yo?'))

class RawQueryTests(TestCase):
    def setUp(self):
        for i in xrange(10):
            MapReduceModel.objects.create(n=i, m=i*2)

    def test_raw_query(self):
        len(MapReduceModel.objects.raw_query({'n' : {'$gt' : 5}})) # 11
        self.assertEqual(
            list(MapReduceModel.objects.filter(n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n' : {'$gt' : 5}}))
        )
        self.assertEqual(
            list(MapReduceModel.objects.filter(n__lt=9, n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n' : {'$lt' : 9}}).filter(n__gt=5)))

    def test_raw_update(self):
        from django.db.models import Q
        MapReduceModel.objects.raw_update(Q(n__lte=3), {'$set' : {'n' : -1}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [-1, -1, -1, -1, 4, 5, 6, 7, 8, 9])
        MapReduceModel.objects.raw_update({'n' : -1}, {'$inc' : {'n' : 2}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [1, 1, 1, 1, 4, 5, 6, 7, 8, 9])


# TODO line breaks
class FullTextTest(TestCase):
    def test_simple_fulltext(self):
        blog = Post(content="simple, full text.... search? test")
        blog.save()

        self.assertEqual(Post.objects.get(content="simple, full text.... search? test"), blog)
        self.assertEqual(Post.objects.get(content_tokenized="simple, search? test"), blog)

    def test_simple_fulltext_filter(self):
        Post(content="simple, fulltext search test").save()
        Post(content="hey, how's, it, going.").save()
        Post(content="this full text search... seems to work... pretty? WELL").save()
        Post(content="I would like to use MongoDB for FULL text search").save()


        self.assertEqual(len(Post.objects.filter(content_tokenized="full text")), 2)
        self.assertEqual(len(Post.objects.filter(content_tokenized="search")), 3)
        self.assertEqual(len(Post.objects.filter(content_tokenized="It-... GoiNg")), 1)

    def test_int_fulltext_lookup(self):
        Post(content="this full text search... seems to work... pretty? WELL").save()
        Post(content="I would like to use MongoDB for FULL text search").save()
        Post(content="just some TEXT without the f u l l  word").save()

        self.assertEqual(len(Post.objects.filter(content_tokenized__in="full text")), 3)

    def test_or_fulltext_queries(self):
        Post(content="Happy New Year Post.... Enjoy").save()
        Post(content="So, Django is amazing, we all know that but django and mongodb is event better ;)").save()
        Post(content="Testing the full text django + mongodb implementation").save()

        self.assertEqual(len(Post.objects.filter(Q(content_tokenized="django mongodb better?") | Q(content_tokenized='full text mongodb'))), 2)

    def test_and_fulltext_queries(self):
        Post(content="Happy New Year Post.... Enjoy").save()
        Post(content="So, Django is amazing, we all know that but django and mongodb is event better ;)").save()
        post = Post(content="Testing the full text django + mongodb implementation")
        post.save()

        self.assertEqual(Post.objects.get(Q(content_tokenized="django mongodb") & Q(content_tokenized='testing')).pk, post.pk)

    def test_for_wrong_lookups(self):
        # This because because full text queries run over 
        # a list of tokenized values so djangotoolbox will complain.
        # We should find a workaround for this. 
        # For example: Using the iexact lookup could be usefule 'cause it
        # could be passed to the tokenized in order to support Case Sensitive 
        # Case Insensitive queries.
        with self.assertRaises(DatabaseError):
            Post.objects.get(content_tokenized__iexact="django mongodb")
            Post.objects.get(content_tokenized__icontains="django mongodb")
