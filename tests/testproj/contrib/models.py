from django.db import models
from django_mongodb_engine.contrib import MongoDBManager

class MapReduceModel(models.Model):
    n = models.IntegerField()
    m = models.IntegerField()

    objects = MongoDBManager()
