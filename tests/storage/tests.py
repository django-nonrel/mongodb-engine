# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import os
import tempfile

from django.core.files.base import ContentFile, File

from django_mongodb_engine.storage import GridFSStorage

from .utils import TestCase


class GridFSStorageTest(TestCase):
    storage_class = GridFSStorage
    temp_dir = tempfile.mktemp()

    def setUp(self):
        self.storage = self.get_storage(self.temp_dir)

    def tearDown(self):
        if hasattr(self.storage, '_db'):
            for collection in self.storage._db.collection_names():
                if not collection.startswith('system.'):
                    self.storage._db.drop_collection(collection)

    def get_storage(self, location, **kwargs):
        return self.storage_class(location=location, **kwargs)

    def test_file_access_options(self):
        """
        Standard file access options are available, and work as
        expected.
        """
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assert_(self.storage.exists('storage_test'))

        test_file = self.storage.open('storage_test', 'r')
        self.assertEqual(test_file.read(), 'storage contents')

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    # def test_file_accessed_time(self):
    #     """
    #     File storage returns a Datetime object for the last accessed
    #     time of a file.
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #     atime = self.storage.accessed_time(f_name)
    #
    #     self.assertEqual(atime, datetime.fromtimestamp(
    #         os.path.getatime(self.storage.path(f_name))))
    #     self.assertTrue(datetime.now() - self.storage.accessed_time(f_name) <
    #                     timedelta(seconds=2))
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

        self.assertTrue(datetime.now() - self.storage.created_time(f_name) <
                        timedelta(seconds=2))
        self.storage.delete(f_name)

    # def test_file_modified_time(self):
    #     """
    #     File storage returns a Datetime object for the last modified
    #     time of a file.
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #     mtime = self.storage.modified_time(f_name)
    #
    #     self.assertTrue(datetime.now() - self.storage.modified_time(f_name) <
    #                     timedelta(seconds=2))
    #
    #     self.storage.delete(f_name)

    def test_file_save_without_name(self):
        """
        File storage extracts the filename from the content object if
        no name is given explicitly.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = ContentFile('custom contents')
        f.name = 'test.file'

        storage_f_name = self.storage.save(None, f)

        self.assertEqual(storage_f_name, f.name)

        self.storage.delete(storage_f_name)

    # def test_file_path(self):
    #     """
    #     File storage returns the full path of a file
    #     """
    #     self.assertFalse(self.storage.exists('test.file'))
    #
    #     f = ContentFile('custom contents')
    #     f_name = self.storage.save('test.file', f)
    #
    #     self.assertEqual(self.storage.path(f_name),
    #         os.path.join(self.temp_dir, f_name))
    #
    #     self.storage.delete(f_name)

    def test_file_url(self):
        """
        File storage returns a url to access a given file from the Web.
        """
        self.assertRaises(ValueError, self.storage.url, 'test.file')

        self.storage = self.get_storage(self.storage.location,
                                        base_url='foo/')
        self.assertEqual(self.storage.url('test.file'),
            '%s%s' % (self.storage.base_url, 'test.file'))

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.assertEqual(self.storage.listdir(''), (set(), []))
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        self.storage.save('storage_test_1', ContentFile('custom content'))
        self.storage.save('storage_test_2', ContentFile('custom content'))
        storage = self.get_storage(location=os.path.join(self.temp_dir,
                                                         'storage_dir_1'))
        storage.save('storage_test_3', ContentFile('custom content'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), set([u'storage_dir_1']))
        self.assertEqual(set(files),
                         set([u'storage_test_1', u'storage_test_2']))


class GridFSStorageTestWithoutLocation(GridFSStorageTest):
    # Now test everything without passing a location argument.
    temp_dir = ''
