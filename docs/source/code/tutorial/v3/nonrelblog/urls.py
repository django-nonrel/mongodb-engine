from django.conf.urls.defaults import patterns, url
from django.views.generic import ListView, DetailView

from models import Post


post_detail = DetailView.as_view(model=Post)
post_list = ListView.as_view(model=Post)

urlpatterns = patterns('',
    url(r'^post/(?P<pk>[a-z\d]+)/$', post_detail, name='post_detail'),
    url(r'^$', post_list, name='post_list'),
)
