from django.db import models

from djangotoolbox.fields import ListField


class Post(models.Model):
    title = models.CharField()
    text = models.TextField()
    tags = ListField()
    comments = ListField()
