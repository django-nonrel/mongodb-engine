from django.contrib.admin import site

from gridfsuploads.models import FileUpload


site.register(FileUpload)
