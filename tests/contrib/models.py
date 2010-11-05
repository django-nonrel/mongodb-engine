from django.db import models
from django_mongodb_engine.contrib import MongoDBManager

class MapReduceModel(models.Model):
    n = models.IntegerField()
    m = models.IntegerField()

    objects = MongoDBManager()

class MapReduceModelWithCustomPrimaryKey(models.Model):
    primarykey = models.CharField(max_length=100, primary_key=True)
    data = models.CharField(max_length=100)
    objects = MongoDBManager()
