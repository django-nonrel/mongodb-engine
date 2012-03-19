from django.db import models

from gridfsuploads import gridfs_storage


class FileUpload(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    file = models.FileField(storage=gridfs_storage, upload_to='/')
