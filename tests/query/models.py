from django.db import models
from django.conf import settings
from djangotoolbox.fields import ListField, RawField

class RawModel(models.Model):
    raw = RawField()

class Empty(models.Model):
    pass

class Blog(models.Model):
    title = models.CharField(max_length=200, db_index=True)

class Post(models.Model):
    title = models.CharField(max_length=200, db_index=True, unique=True)
    content = models.CharField(max_length=1000)
    date_published = models.DateTimeField(null=True, blank=True)
    blog = models.ForeignKey(Blog, null=True, blank=True)

class Person(models.Model):
    name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    age = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("name", "surname")

class DateModel(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    time = models.TimeField(null=True)
    date = models.DateField(null=True)
    _datelist_default = []
    datelist = ListField(models.DateField(), default=_datelist_default)

class Article(models.Model):
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()

    class Meta:
       ordering = ('pub_date',)

    def __unicode__(self):
        return self.headline
