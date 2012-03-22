from mimetypes import guess_type

from django.conf import settings
from django.http import HttpResponse, Http404

from gridfs.errors import NoFile
from gridfsuploads import gridfs_storage
from gridfsuploads.models import FileUpload


if settings.DEBUG:

    def serve_from_gridfs(request, path):
        # Serving GridFS files through Django is inefficient and
        # insecure. NEVER USE IN PRODUCTION!
        try:
            gridfile = gridfs_storage.open(path)
        except NoFile:
            raise Http404
        else:
            return HttpResponse(gridfile, mimetype=guess_type(path)[0])
