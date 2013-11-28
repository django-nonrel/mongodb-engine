from django.db import models

from djangotoolbox.fields import ListField, EmbeddedModelField

from django_mongodb_engine.contrib import MongoDBManager


class Post(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField(max_length=100)
    text = models.TextField()
    tags = ListField()
    comments = ListField(EmbeddedModelField('Comment')) # <---

    objects = MongoDBManager()


class Comment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    author = EmbeddedModelField('Author')
    text = models.TextField()


class Author(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.email)
