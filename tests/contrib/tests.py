from django.test import TestCase
from .models import *
from django_mongodb_engine.contrib.mapreduce import MapReduceResult

class SimpleTest(TestCase):
    #def test_mixin(self):
    #    self.assert_(MapReduceModel.mongodb.model is not None)
    #    self.assertNotEqual(MapReduceModel._default_manager,
    #                        MapReduceModel.mongodb)

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

        finalizefunc = """ function(key, value) { return value * 2 } """

        random_numbers = [
            (3, 4),
            (6, 19),
            (5, 8),
            (0, 20), # this instance won't be emitted by `map`
            (300, 10),
            (2, 77)
        ]

        for n, m in random_numbers:
            MapReduceModel(n=n, m=m).save()

        # Test mapfunc + reducefunc
        documents = list(MapReduceModel.objects.map_reduce(mapfunc, reducefunc))
        self.assertEqual(len(documents), len(random_numbers)-1)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum(n*m for n, m in random_numbers))

        obj = documents[0].get_object()
        self.assert_(isinstance(obj, MapReduceModel))
        self.assertEqual((obj.n, obj.m), random_numbers[0])
        self.assert_(obj.id)

        # Test finalizefunc and limit
        documents = list(MapReduceModel.objects.map_reduce(
                            mapfunc, reducefunc, finalizefunc, limit=3))
        self.assertEqual(len(documents), 3)
        self.assertEqual(sum(doc.value for doc in documents),
                         sum((n*m)*2 for n, m in random_numbers[:3]))

        # Test scope
        mapfunc = """
            function() { emit(this._id, this.n * x) } """
        reducefunc = """
            function(key, values) { return values[0] * y } """
        scope = {'x' : 5, 'y' : 10}
        documents = list(MapReduceModel.objects.map_reduce(mapfunc, reducefunc,
                                                           scope=scope))
        self.assertEqual([document.value for document in documents],
                         [(n*scope['x']) * scope['y'] for n, m in random_numbers])

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
            mapfunc, reducefunc)
        somedoc = documents[0]
        self.assertEqual(somedoc.key, 'bar') # ordered by pk
        self.assertEqual(somedoc.value, None)
        obj = somedoc.get_object()
        self.assert_(not hasattr(obj, 'id') and not hasattr(obj, '_id'))
        self.assertEqual(obj, MapReduceModelWithCustomPrimaryKey(pk='bar', data='yo?'))

    def test_raw_query(self):
        for i in xrange(10):
            MapReduceModel.objects.create(n=i, m=i*2)

        self.assertEqual(
            list(MapReduceModel.objects.filter(n__gt=5)),
            list(MapReduceModel.objects.raw_query({'n' : {'$gt' : 5}}))
        )

        self.assertRaises(TypeError,
            lambda: len(MapReduceModel.objects.raw_query().filter(n__gt=5))
        )

        from django.db.models import Q
        MapReduceModel.objects.raw_update(Q(n__lte=3), {'$set' : {'n' : -1}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [-1, -1, -1, -1, 4, 5, 6, 7, 8, 9])
        MapReduceModel.objects.raw_update({'n' : -1}, {'$inc' : {'n' : 2}})
        self.assertEqual([o.n for o in MapReduceModel.objects.all()],
                         [1, 1, 1, 1, 4, 5, 6, 7, 8, 9])
