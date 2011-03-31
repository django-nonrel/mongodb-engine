from django.test import TestCase
from django.conf import settings
from django.db import connections
from django.db.models import Model

class TestCase(TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        if getattr(settings, 'TEST_DEBUG', False):
            settings.DEBUG = True

def skip_all_except(*tests):
    class meta(type):
        def __new__(cls, name, bases, dict):
            for attr in dict.keys():
                if attr.startswith('test_') and attr not in tests:
                    del dict[attr]
            return type.__new__(cls, name, bases, dict)
    return meta

def skip(test):
    pass

def get_collection(model_or_name):
    if isinstance(model_or_name, Model):
        model_or_name = model._meta.db_table
    return connections['default'].get_collection(model_or_name)
