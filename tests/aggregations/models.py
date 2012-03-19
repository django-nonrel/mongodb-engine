from django.db import models


class Person(models.Model):
    age = models.IntegerField()
    birthday = models.DateTimeField()
