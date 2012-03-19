from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('gridfsuploads.views',
    ('^(?P<path>.+)', 'serve_from_gridfs'),
)
