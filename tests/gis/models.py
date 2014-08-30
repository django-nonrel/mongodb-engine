from django.db import models
from django_mongodb_engine.contrib import GeoMongoDBManager
from django_mongodb_engine.fields import GeometryField


class GeometryModel(models.Model):
    geom = GeometryField()

    objects = GeoMongoDBManager()

    class MongoMeta:
        indexes = [{'fields': [('geom', '2dsphere')]}]