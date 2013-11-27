from django.db import models
from djangotoolbox.fields import ListField, DictField, EmbeddedModelField
from django_mongodb_engine.contrib import MongoDBManager


class DotQueryEmbeddedModel(models.Model):
    f_int = models.IntegerField()


class DotQueryTestModel(models.Model):
    objects = MongoDBManager()

    f_id = models.IntegerField()
    f_dict = DictField(db_column='test_dict')
    f_list = ListField()
    f_embedded = EmbeddedModelField(DotQueryEmbeddedModel)
    f_embedded_list = ListField(EmbeddedModelField(DotQueryEmbeddedModel))
