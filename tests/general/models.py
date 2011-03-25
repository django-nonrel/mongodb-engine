from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from djangotoolbox.fields import ListField, DictField, SetField, RawField

ON_SQLITE = 'sqlite' in settings.DATABASES['default']['ENGINE']

class Blog(models.Model):
    title = models.CharField(max_length=200, db_index=True)

class Simple(models.Model):
    a = models.IntegerField()

class IndexTestModel(models.Model):
    regular_index = models.IntegerField(db_index=True)
    custom_column = models.IntegerField(db_column='foo', db_index=True)
    descending_index = models.IntegerField()
    descending_index_custom_column = models.IntegerField(db_column='bar')
    foreignkey_index = models.ForeignKey(Simple, db_index=True)
    foreignkey_custom_column = models.ForeignKey('Entry', db_column='spam')

    class MongoMeta:
        descending_indexes = ['descending_index', 'descending_index_custom_column']
        index_together = ['regular_index', 'custom_column']

class Entry(models.Model):
    title = models.CharField(max_length=200, db_index=True, unique=True)
    content = models.CharField(max_length=1000)
    date_published = models.DateTimeField(null=True, blank=True)
    blog = models.ForeignKey(Blog, null=True, blank=True)

    class MongoMeta:
        descending_indexes = ['title']

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
    if not ON_SQLITE:
        _datelist_default = []
        datelist = ListField(models.DateField(), default=_datelist_default)

if not ON_SQLITE:
    class DynamicModel(models.Model):
        gen = RawField()

    class TestFieldModel(models.Model):
        title = models.CharField(max_length=200)
        mlist = ListField()
        mlist_default = ListField(default=["a", "b"])
        slist = ListField(ordering=lambda x:x)
        slist_default = ListField(default=["b", "a"], ordering=lambda x:x)
        mdict = DictField()
        mdict_default = DictField(default={"a": "a", 'b':1})
        mset = SetField()
        mset_default = SetField(default=set(["a", 'b']))

        class MongoMeta:
            index_together = [{'fields' : [ ('title', -1), 'mlist']}]
