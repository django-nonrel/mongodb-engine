import os
from django.test import TestCase

from django.core.files.base import File

import models

from django_mongodb_engine.storage import GridFsStorage

class SimpleTest(TestCase):
        
    def test_store_file(self):
        storage = GridFsStorage("/some/path")
        f = File(open(models.__file__, "r"))
        storage.save("models.py", f)
        
        storage = GridFsStorage("/some/")
        f = File(open(models.__file__, "r"))
        storage.save("models.py", f)
        
        self.assertEqual(storage.listdir("path"), (["/some/path"], ['models.py']))
        
        storage = GridFsStorage("/")
        self.assertEqual(storage.listdir(""), (["/some"], []))
