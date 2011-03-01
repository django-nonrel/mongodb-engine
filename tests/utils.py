from django.test import TestCase
from django.conf import settings
from django.db import connections

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

def get_collection(model):
    return connections['default'].get_collection(model._meta.db_table)
