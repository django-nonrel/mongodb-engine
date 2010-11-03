from django.test import TestCase
from .models import Simple
from django.db.models import Q
from django.db.utils import DatabaseError

class SimpleTest(TestCase):
    def assertEqualQueryset(self, a, b):
        self.assertEqual(list(a), list(b))

    def test_simple(self):
        obj1 = Simple.objects.create(a=1)
        obj2 = Simple.objects.create(a=1)
        obj3 = Simple.objects.create(a=2)
        obj4 = Simple.objects.create(a=3)

        self.assertEqualQueryset(
            Simple.objects.filter(a=1),
            [obj1, obj2]
        )
        self.assertEqualQueryset(
            Simple.objects.filter(a=1) | Simple.objects.filter(a=2),
            [obj1, obj2, obj3]
        )
        self.assertEqualQueryset(
            Simple.objects.filter(Q(a=2) | Q(a=3)),
            [obj3, obj4]
        )

        self.assertEqualQueryset(
            Simple.objects.filter(Q(Q(a__lt=4) & Q(a__gt=2)) | Q(a=1)),
            [obj1, obj2, obj4]
        )

    def test_nested(self):
        objs = [Simple.objects.create(a=i) for i in xrange(10)]
        self.assertEqualQueryset(
            Simple.objects.filter(Q(a=2) | Q(Q(Q(a__gt=3) & Q(a__lt=8)) | Q(a=9))),
            [objs[2]] +  objs[4:8] + [objs[9]]
        )

    def test_crazy(self):
        objs = [Simple.objects.create(a=i, b=i**2) for i in xrange(50)]
        self.assertRaises(
            DatabaseError,
            list, Simple.objects.filter(Q(a__in=[3, 4, 5,6 ]), Q(b__in=[25, 36]))
                   | Simple.objects.filter(Q(b=48**2) | Q(b=49**2))
        )
