from django_mongodb_engine.query import A

from .models import *
from .utils import TestCase, get_collection


class EmbeddedModelFieldTestCase(TestCase):

    def test_legacy_field(self):
        # LegacyModelField should behave like EmbeddedLegacyModelField
        # for "new-style" data sets.
        LegacyModel.objects.create(legacy=EmbeddedModel(charfield='blah'))
        self.assertEqual(LegacyModel.objects.get().legacy.charfield, u'blah')

        # LegacyModelField should keep the embedded model's 'id' if the data
        # set contains it. To add one, we have to do a manual update here:
        collection = get_collection(LegacyModel)
        collection.update({}, {'$set': {'legacy._id': 42}}, safe=True)
        self.assertEqual(LegacyModel.objects.get().legacy.id, 42)

        # If the data record contains '_app' or '_model', they should
        # be stripped out so the resulting model instance is not
        # populated with them.
        collection.update(
            {}, {'$set': {'legacy._model': 'a', 'legacy._app': 'b'}},
            safe=True)
        self.assertFalse(hasattr(LegacyModel.objects.get().legacy, '_model'))
        self.assertFalse(hasattr(LegacyModel.objects.get().legacy, '_app'))

    def test_query_embedded(self):
        Model(x=3, em=EmbeddedModel(charfield='foo')).save()
        obj = Model(x=3, em=EmbeddedModel(charfield='blurg'))
        obj.save()
        Model(x=3, em=EmbeddedModel(charfield='bar')).save()
        obj_from_db = Model.objects.get(em=A('charfield', 'blurg'))
        self.assertEqual(obj, obj_from_db)
