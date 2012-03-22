from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_mongodb_engine.contrib import MongoDBManager
from django_mongodb_engine.contrib.search.fields import TokenizedField


class MapReduceModel(models.Model):
    n = models.IntegerField()
    m = models.IntegerField()

    objects = MongoDBManager()


class MapReduceModelWithCustomPrimaryKey(models.Model):
    primarykey = models.CharField(max_length=100, primary_key=True)
    data = models.CharField(max_length=100)
    objects = MongoDBManager()


class Post(models.Model):
    content = TokenizedField(max_length=255)

    def __unicode__(self):
        return "Post"
