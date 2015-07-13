from __future__ import with_statement
from django.db.models import Q
from models import *
from utils import *


class DotQueryTests(TestCase):
    """Tests for querying on foo.bar using join syntax."""

    def setUp(self):
        fm = DotQueryForeignModel.objects.create(
            f_char='hello',
        )
        DotQueryTestModel.objects.create(
            f_id=51,
            f_dict={'numbers': [1, 2, 3], 'letters': 'abc'},
            f_list=[{'color': 'red'}, {'color': 'blue'}],
            f_embedded=DotQueryEmbeddedModel(f_int=10, f_foreign=fm),
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
                DotQueryEmbeddedModel(f_int=110, f_foreign=fm),
                DotQueryEmbeddedModel(f_int=111, f_foreign=fm),
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
        DotQueryForeignModel.objects.all().delete()

    def test_dict_queries(self):
        qs = DotQueryTestModel.objects.filter(f_dict__numbers=2)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].f_id, 51)
        self.assertEqual(qs[1].f_id, 52)
        qs = DotQueryTestModel.objects.filter(f_dict__letters__contains='b')
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].f_id, 51)
        self.assertEqual(qs[1].f_id, 52)
        qs = DotQueryTestModel.objects.exclude(f_dict__letters__contains='b')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].f_id, 53)
        qs = DotQueryTestModel.objects.exclude(f_dict__letters__icontains='B')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].f_id, 53)

    def test_list_queries(self):
        qs = DotQueryTestModel.objects.filter(f_list__color='red')
        qs = qs.exclude(f_list__color='green')
        qs = qs.exclude(f_list__color='purple')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].f_id, 51)

    def test_embedded_queries(self):
        qs = DotQueryTestModel.objects.exclude(f_embedded__f_int__in=[10, 12])
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].f_id, 52)

    def test_embedded_list_queries(self):
        qs = DotQueryTestModel.objects.get(f_embedded_list__f_int=120)
        self.assertEqual(qs.f_id, 53)

    def test_foreign_queries(self):
        fm = DotQueryForeignModel.objects.get(f_char='hello')
        qs = DotQueryTestModel.objects.get(f_embedded__f_foreign=fm)
        self.assertEqual(qs.f_id, 51)
        qs = DotQueryTestModel.objects.get(f_embedded_list__f_foreign=fm)
        self.assertEqual(qs.f_id, 52)
        qs = DotQueryTestModel.objects.get(f_embedded__f_foreign__pk=fm.pk)
        self.assertEqual(qs.f_id, 51)
        qs = DotQueryTestModel.objects.get(f_embedded_list__f_foreign__pk__exact=fm.pk)
        self.assertEqual(qs.f_id, 52)

    def test_q_queries(self):
        q = Q(f_dict__numbers=1) | Q(f_dict__numbers=4)
        q = q & Q(f_dict__numbers=3)
        qs = DotQueryTestModel.objects.filter(q)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].f_id, 51)
        self.assertEqual(qs[1].f_id, 53)

    def test_save_after_query(self):
        qs = DotQueryTestModel.objects.get(f_dict__letters='cd')
        self.assertEqual(qs.f_id, 53)
        qs.f_id = 1053
        qs.clean()
        qs.save()
        qs = DotQueryTestModel.objects.get(f_dict__letters='cd')
        self.assertEqual(qs.f_id, 1053)
        qs.f_id = 53
        qs.clean()
        qs.save()
        qs = DotQueryTestModel.objects.get(f_dict__letters='cd')
        self.assertEqual(qs.f_id, 53)
