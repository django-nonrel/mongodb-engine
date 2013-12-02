from __future__ import with_statement
from django.db.models import Q
from models import *
from utils import *

class DotQueryTests(TestCase):
    """Tests for querying on foo.bar using join syntax."""

    def setUp(self):
        DotQueryTestModel.objects.create(
            f_id=51,
            f_dict={'numbers': [1, 2, 3], 'letters': 'abc'},
            f_list=[{'color': 'red'}, {'color': 'blue'}],
            f_embedded=DotQueryEmbeddedModel(f_int=10),
            f_embedded_list=[
                DotQueryEmbeddedModel(f_int=100),
                DotQueryEmbeddedModel(f_int=101),
            ],
        )
        DotQueryTestModel.objects.create(
            f_id=52,
            f_dict={'numbers': [2, 3], 'letters': 'bc'},
            f_list=[{'color': 'red'}, {'color': 'green'}],
            f_embedded=DotQueryEmbeddedModel(f_int=11),
            f_embedded_list=[
                DotQueryEmbeddedModel(f_int=110),
                DotQueryEmbeddedModel(f_int=111),
            ],
        )
        DotQueryTestModel.objects.create(
            f_id=53,
            f_dict={'numbers': [3, 4], 'letters': 'cd'},
            f_list=[{'color': 'yellow'}, {'color': 'orange'}],
            f_embedded=DotQueryEmbeddedModel(f_int=12),
            f_embedded_list=[
                DotQueryEmbeddedModel(f_int=120),
                DotQueryEmbeddedModel(f_int=121),
            ],
        )

    def tearDown(self):
        DotQueryTestModel.objects.all().delete()

    def test_dict_queries(self):
        q = DotQueryTestModel.objects.filter(f_dict__numbers=2)
        self.assertEqual(q.count(), 2)
        self.assertEqual(q[0].f_id, 51)
        self.assertEqual(q[1].f_id, 52)
        q = DotQueryTestModel.objects.filter(f_dict__letters__contains='b')
        self.assertEqual(q.count(), 2)
        self.assertEqual(q[0].f_id, 51)
        self.assertEqual(q[1].f_id, 52)
        q = DotQueryTestModel.objects.exclude(f_dict__letters__contains='b')
        self.assertEqual(q.count(), 1)
        self.assertEqual(q[0].f_id, 53)

    def test_list_queries(self):
        q = DotQueryTestModel.objects.filter(f_list__color='red')
        q = q.exclude(f_list__color='green')
        q = q.exclude(f_list__color='purple')
        self.assertEqual(q.count(), 1)
        self.assertEqual(q[0].f_id, 51)

    def test_embedded_queries(self):
        q = DotQueryTestModel.objects.exclude(f_embedded__f_int__in=[10, 12])
        self.assertEqual(q.count(), 1)
        self.assertEqual(q[0].f_id, 52)

    def test_embedded_list_queries(self):
        q = DotQueryTestModel.objects.get(f_embedded_list__f_int=120)
        self.assertEqual(q.f_id, 53)

#   FIXME: Need to implement Q on dot fields
#   def test_q_queries(self):
#       q = DotQueryTestModel.objects.filter(Q(f_dict__numbers=1)|Q(f_dict__numbers=4))
#       self.assertEqual(q.count(), 2)
#       self.assertEqual(q[0].f_id, 51)
#       self.assertEqual(q[1].f_id, 53)

    def test_save_after_query(self):
        q = DotQueryTestModel.objects.get(f_dict__letters='cd')
        self.assertEqual(q.f_id, 53)
        q.f_id = 1053
        q.clean()
        q.save()
        q = DotQueryTestModel.objects.get(f_dict__letters='cd')
        self.assertEqual(q.f_id, 1053)
        q.f_id = 53
        q.clean()
        q.save()
        q = DotQueryTestModel.objects.get(f_dict__letters='cd')
        self.assertEqual(q.f_id, 53)
