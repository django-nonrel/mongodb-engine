from django.test import TestCase
from django.conf import settings

class TestCase(TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        if getattr(settings, 'TEST_DEBUG', False):
            settings.DEBUG = True
