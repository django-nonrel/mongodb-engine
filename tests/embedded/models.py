from django.db import models

from djangotoolbox.fields import DictField, EmbeddedModelField


class EmbeddedModel(models.Model):
    charfield = models.CharField(max_length=3, blank=False)
    datetime = models.DateTimeField(null=True)
    datetime_auto_now_add = models.DateTimeField(auto_now_add=True)
    datetime_auto_now = models.DateTimeField(auto_now=True)


class Model(models.Model):
    x = models.IntegerField()
    em = EmbeddedModelField(EmbeddedModel)
    dict_emb = DictField(EmbeddedModelField(EmbeddedModel))


# Docstring example copy.
class Address(models.Model):
    street = models.CharField(max_length=200)
    postal_code = models.IntegerField()
    city = models.CharField(max_length=100)


class Customer(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = EmbeddedModelField(Address)
