from mimetypes import guess_type
from gridfs.errors import NoFile
from django.http import HttpResponse, Http404
from django.conf import settings
from gridfsuploads import gridfs_storage
from gridfsuploads.models import FileUpload

if settings.DEBUG:
    # Serving GridFS files through Django is inefficient and insecure.
    # NEVER USE IN PRODUCTION!
    def serve_from_gridfs(request, path):
        try:
            gridfile = gridfs_storage.open(path)
        except NoFile:
            raise Http404
        else:
            return HttpResponse(gridfile, mimetype=guess_type(path)[0])
