from django.test import TestCase
from datetime import datetime
from models import Person

class SimpleTest(TestCase):
    def test_aggregations(self):
        for age, birthday in (
            [4,  (2007, 12, 25)],
            [4,  (2006, 1, 1)],
            [1,  (2008, 12, 1)],
            [4,  (2006, 6, 1)],
            [12, (1998, 9, 1)]
        ):
            Person.objects.create(age=age, birthday=datetime(*birthday))

        from django.db.models.aggregates import Count, Sum
        from django_mongodb_engine.contrib.aggregations import Max, Min, Avg

        aggregates = Person.objects.aggregate(Min("age"), Max("age"), Avg("age"))
        self.assertEqual(aggregates, {'age__min': 1, 'age__avg': 5.0, 'age__max': 12})

        #with filters and testing the sqlaggregates->mongoaggregate conversion
        aggregates = Person.objects.filter(age__gte=4).aggregate(Min("birthday"), Max("birthday"), Avg("age"), Count("id"))
        self.assertEqual(aggregates, {'birthday__max': datetime(2007, 12, 25, 0, 0),
                                      'birthday__min': datetime(1998, 9, 1, 0, 0),
                                      'age__avg': 6.0,
                                      'id__count': 4})

        self.assertRaises(NotImplementedError, Person.objects.aggregate, Sum('age'))
