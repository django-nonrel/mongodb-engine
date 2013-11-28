from django.db import models

from django_mongodb_engine.contrib import MongoDBManager


class Article(models.Model):
    author = models.ForeignKey('Author')
    text = models.TextField()

    objects = MongoDBManager()


class Author(models.Model):
    pass
