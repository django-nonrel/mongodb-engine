from django.db import models
from djangotoolbox.fields import DictField
from django_mongodb_engine.fields import EmbeddedModelField

class EmbeddedModel(models.Model):
    charfield = models.CharField(max_length=3, blank=False)
    datetime = models.DateTimeField(null=True)
    datetime_auto_now_add = models.DateTimeField(auto_now_add=True)
    datetime_auto_now = models.DateTimeField(auto_now=True)

class Model(models.Model):
    x = models.IntegerField()
    em = EmbeddedModelField(EmbeddedModel)
    dict_emb = DictField()
