"""
Test suite for django-mongodb-engine.
"""

from django.test import TestCase
from models import *

class FullTextTest(TestCase):

    def test_simple_fulltext(self):
        blog = Blog(content="simple, full text.... search? test")
        blog.save()

        self.assertEqual(Blog.objects.get(content="simple, full text.... search? test"), blog)

        Blog(content="simple, fulltext search test").save()
        Blog(content="hey, how's, it, going.").save()
        Blog(content="this full text search... seems to work... pretty? WELL").save()
        Blog(content="I would like to use MongoDB for FULL text search").save()


        self.assertEqual(len(Blog.objects.filter(content_analyzed="full text")), 3)
        self.assertEqual(len(Blog.objects.filter(content_analyzed="search")), 4)
        self.assertEqual(len(Blog.objects.filter(content_analyzed="It-... GoiNg")), 1)