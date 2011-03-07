# -*- coding: utf-8 -*-
import os
import tempfile
from datetime import datetime, timedelta
from django.core.files.base import ContentFile, File
from django_mongodb_engine.storage import GridFsStorage

from .utils import TestCase
import models

FILES_PATH = os.path.join(os.path.dirname(models.__file__), 'to_import')

class GridFsStorageTest(TestCase):
    storage_class = GridFsStorage

    def setUp(self):
        self.temp_dir = tempfile.mktemp()
        self.storage = self.storage_class(location=self.temp_dir, base_url='/test_media_url/')

    def test_file_access_options(self):
        """
        Standard file access options are available, and work as expected.
        """
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assert_(self.storage.exists('storage_test'))

        test_file =  self.storage.open('storage_test', 'r')
        self.assertEqual(test_file.read(), 'storage contents')

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    # def test_file_accessed_time(self):
    #     """
    #     File storage returns a Datetime object for the last accessed time of
    #     a file.
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #     atime = self.storage.accessed_time(f_name)
    #
    #     self.assertEqual(atime, datetime.fromtimestamp(
    #         os.path.getatime(self.storage.path(f_name))))
    #     self.assertTrue(datetime.now() - self.storage.accessed_time(f_name) < timedelta(seconds=2))
    #     self.storage.delete(f_name)

    def test_file_created_time(self):
        """
        File storage returns a Datetime object for the creation time of
        a file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)
        ctime = self.storage.created_time(f_name)

        self.assertTrue(datetime.now() - self.storage.created_time(f_name) < timedelta(seconds=2))
        self.storage.delete(f_name)

    # def test_file_modified_time(self):
    #     """
    #     File storage returns a Datetime object for the last modified time of
    #     a file.
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #     mtime = self.storage.modified_time(f_name)
    #
    #     self.assertTrue(datetime.now() - self.storage.modified_time(f_name) < timedelta(seconds=2))
    #
    #     self.storage.delete(f_name)

    def test_file_save_without_name(self):
        """
        File storage extracts the filename from the content object if no
        name is given explicitly.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f.name = 'test.file'

        storage_f_name = self.storage.save(None, f)

        self.assertEqual(storage_f_name, f.name)

        self.storage.delete(storage_f_name)

    def test_file_path(self):
        """
        File storage returns the full path of a file
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assertEqual(self.storage.path(f_name),
            os.path.join(self.temp_dir, f_name))

        self.storage.delete(f_name)

    # def test_file_url(self):
    #     """
    #     File storage returns a url to access a given file from the Web.
    #     """
    #     self.assertEqual(self.storage.url('test.file'),
    #         '%s%s' % (self.storage.base_url, 'test.file'))
    #
    #     self.storage.base_url = None
    #     self.assertRaises(ValueError, self.storage.url, 'test.file')

    def test_file_with_mixin(self):
        """
        File storage can get a mixin to extend the functionality of the
        returned file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        class TestFileMixin(object):
            mixed_in = True

        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assert_(isinstance(
            self.storage.open('test.file', mixin=TestFileMixin),
            TestFileMixin
        ))

        self.storage.delete('test.file')

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        f = self.storage.save('storage_test_1', ContentFile('custom content'))
        f = self.storage.save('storage_test_2', ContentFile('custom content'))
        storage = GridFsStorage(location=os.path.join(self.temp_dir, 'storage_dir_1'))
        f = storage.save('storage_test_3', ContentFile('custom content'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), set([u'storage_dir_1']))
        self.assertEqual(set(files),
                         set([u'storage_test_1', u'storage_test_2']))

        self.storage.delete('storage_test_1')
        self.storage.delete('storage_test_2')
