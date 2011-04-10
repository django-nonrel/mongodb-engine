import os
import re

import gridfs

from django.conf import settings
from django.core.files.storage import Storage

from .utils import get_default_connection

class GridFsStorage(Storage):
    """
    GridFs Storage Backend for django.

    This backend aims to add a gridfs storage to upload files to
    using django file fields.

    The reason why a folders are converted into collections names is to
    improve performance. For example:

    To list a directory '/this/path/' we would have to execute a list
    over the whole collection and then filter the list excluding those not
    starting by '/this/path'. This implementation does something similar but it lists
    the collections and filters the collections names to know what 'directories'
    are contained inside /this/path and then lists the collection to get the files.


    THIS IS UNDER EVALUATION. PLEASE SHARE YOUR COMMENTS AND THOUGHTS.

    TO BE IMPROVED.
    """

    def __init__(self, location=None, base_url=None, prefix='storage', sep='/'):
        if location is None:
            location = settings.MEDIA_ROOT
        if base_url is None:
            base_url = settings.MEDIA_URL
        self.location = os.path.abspath(location)
        self.base_url = base_url
        self.sep = sep
        self.prefix = prefix

    @property
    def fs(self):
        """
        Gets the GridFs instance and returns it.
        """
        if not hasattr(self, '_fs'):
            self._fs = self._get_path_instance(self.location)
        return self._fs

    def _get_path_instance(self, path):
        return gridfs.GridFS(get_default_db_connection(), self._get_collection_name_for(path))

    def _get_collection_name_for(self, path="/"):
        col_name = self.path(path).replace(os.sep, self.sep)
        if col_name == self.sep:
            col_name = ""
        return "%s%s" % (self.prefix, col_name)

    def _get_abs_path_name_for(self, collection):
        if collection.endswith(".files"):
            collection = collection[:-6]
        path = collection.replace(self.sep, os.sep)[len(self.prefix):]
        return path and path or "/"

    def _get_rel_path_name_for(self, collection):
        path = self._get_abs_path_name_for(collection)
        return os.path.relpath(path, self.path(""))

    def _get_file(self, path):
        """
        Gets the last version of path.
        """
        try:
            return self.fs.get_last_version(filename=path)
        except gridfs.errors.NoFile:
            return None

    def _open(self, name, mode='rb'):
        """
        Opens a file and returns it.
        """
        if "w" in mode and not self.exists(name):
            return self.fs.new_file(filename=name)

        doc = self._get_file(name)
        if doc:
            return doc
        else:
            raise ValueError("No such file or directory: '%s'" % name)

    def _save(self, name, content):
        self.fs.put(content, filename=name)
        return name

    def delete(self, name):
        """
        Deletes the doc if it exists.
        """
        doc = self._get_file(name)
        if doc:
            self.fs.delete(doc._id)

    def path(self, name):
        return os.path.abspath(os.path.join(self.location, name))

    def exists(self, name):
        return self.fs.exists(filename=name)

    def listdir(self, path):
        """
        Right now it gets the collections names and filters the list to keep
        just the ones belonging to path and then gets the files inside the fs.

        Needs to be improved
        """

        col_name = self._get_collection_name_for(path)
        path_containing_dirs = re.compile(r"^%s(%s\w+){1}\.files$" % (re.escape(col_name), re.escape(self.sep)))
        collections = filter(lambda x: path_containing_dirs.match(x), get_default_db_connection().collection_names())
        return [self._get_rel_path_name_for(col) for col in collections], self.fs.list()

    def size(self, name):
        doc = self._get_file(name)
        if doc:
            return doc.length
        else:
            raise ValueError("No such file or directory: '%s'" % name)

    def created_time(self, name):
        doc = self._get_file(name)
        if doc:
            return doc.upload_date
        else:
            raise ValueError("No such file or directory: '%s'" % name)
