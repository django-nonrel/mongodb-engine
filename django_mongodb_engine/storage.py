import os
import re
from gridfs import GridFS
from pymongo.objectid import ObjectId

from django.conf import settings
from django.core.files.storage import Storage

from .utils import get_default_db_connection

class GridFsStorage(Storage):

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = settings.MEDIA_ROOT
        if base_url is None:
            base_url = settings.MEDIA_URL
        self.location = os.path.abspath(location)
        self.base_url = base_url
            
    @property
    def fs(self):
        if not hasattr(self, '_fs'):
            self._fs = self._get_path_instance(self.location)
        return self._fs
        
    def _get_path_instance(self, path):
        return GridFS(get_default_db_connection(), self._get_collection_name_for(path))
        
    def _get_collection_name_for(self, path="/"):
        col_name = self.location.replace("/", "_")
        if col_name == "_":
            col_name = ""
        return "fs%s" % col_name
        
    def _get_path_name_for(self, collection):
        if collection.endswith(".files"):
            collection = collection[:-6]
        path = collection.replace("_", "/")[2:]
        return path and path or "/"
        
    def _open(self, name, mode='rb'):
        return self.fs.get_last_version(filename=name)

    def _save(self, name, content):
        file_obj = self.fs.new_file(filename=name)

        for chunk in content.chunks():
            file_obj.write(chunk)
        file_obj.close()
        return name
           
    def delete(self, name):
        doc = self.fs.get_last_version(name)
        if doc:
            self.fs.delete(doc.id)
            
    def path(self, name):
        return os.path.join(self.location, name)
        
    def exists(self, name):
        return self.fs.exists(filename=name)
        
    def listdir(self, path):
        path = self.path(path)
        col_name = self._get_collection_name_for(path)
        path_containing_dirs = re.compile(r"^%s(_[a-zA-Z0-9]+){1}\.files$" % col_name)
        collections = filter(lambda x: path_containing_dirs.match(x), get_default_db_connection().collection_names())
        return [self._get_path_name_for(col) for col in collections], self.fs.list()
        
    def size(self, name):
        return self.fs.get_last_version(name).length
        
    def url(self, name):
        raise NotImplementedError
