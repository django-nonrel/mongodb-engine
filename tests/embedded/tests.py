from django_mongodb_engine.query import A

from models import *
from utils import TestCase, get_collection


class EmbeddedModelFieldTestCase(TestCase):

    def test_query_embedded(self):
        Model(x=3, em=EmbeddedModel(charfield='foo')).save()
        obj = Model(x=3, em=EmbeddedModel(charfield='blurg'))
        obj.save()
        Model(x=3, em=EmbeddedModel(charfield='bar')).save()
        obj_from_db = Model.objects.get(em=A('charfield', 'blurg'))
        self.assertEqual(obj, obj_from_db)
