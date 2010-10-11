from django.test import TestCase
from django.db.utils import DatabaseError
from .models import *
from datetime import datetime
import time

def skip(func):
    pass

class EmbeddedModelFieldTestCase(TestCase):
    @skip
    def test_empty(self):
        obj = Model(x=5)
        self.assertRaises(DatabaseError, obj.save)

    @skip
    def test_empty_embedded(self):
        obj = Model(x=5, em=EmbeddedModel())
        self.assertRaises(DatabaseError, obj.save)

    def test_simple(self):
        obj = Model(x=5, em=EmbeddedModel(charfield='foo'))
        assert obj.em
        obj.save()
        obj = Model.objects.get()
        self.assertTrue(isinstance(obj.em, EmbeddedModel))
        self.assertEqual(obj.em.charfield, 'foo')
        self.assertEqual(obj.em.id, None)
        self.assertNotEqual(obj.em.datetime_auto_now, None)
        self.assertNotEqual(obj.em.datetime_auto_now_add, None)
        time.sleep(1) # sorry for that, FIXME!
        obj.save()
        auto_now_before = obj.em.datetime_auto_now
        obj = Model.objects.get()
        self.assertNotEqual(obj.em.datetime_auto_now,
                            auto_now_before)

    def test_in_dictfield(self):
        foodate = datetime(year=2003, month=9, day=23)
        obj = Model(
            x=5,
            em=EmbeddedModel(charfield='hello', datetime=foodate),
            dict_emb={'blah' : EmbeddedModel(charfield='blurg')}
        )
        obj.dict_emb['lala'] = EmbeddedModel(charfield='blubb',
                                             datetime=foodate)
        obj.save()
        obj = Model.objects.get()
        self.assertEqual(obj.em.datetime, foodate)
        self.assertEqual(obj.dict_emb['blah'].charfield, 'blurg')
        self.assertEqual(obj.dict_emb['lala'].datetime, foodate)
        obj.dict_emb['foo'] = EmbeddedModel(charfield='bar')
        time.sleep(1) # sorry for that, FIXME!
        obj.save()
        auto_now_before = obj.dict_emb['blah'].datetime_auto_now
        obj = Model.objects.get()
        self.assertNotEqual(obj.dict_emb['blah'].datetime_auto_now,
                            auto_now_before)
        self.assertEqual(obj.dict_emb['foo'].charfield, 'bar')
