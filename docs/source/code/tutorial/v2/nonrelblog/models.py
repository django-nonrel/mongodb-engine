from django.db import models

from djangotoolbox.fields import ListField, EmbeddedModelField


class Post(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField()
    text = models.TextField()
    tags = ListField()
    comments = ListField(EmbeddedModelField('Comment')) # <---


class Comment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    author = EmbeddedModelField('Author')
    text = models.TextField()


class Author(models.Model):
    name = models.CharField()
    email = models.EmailField()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.email)
