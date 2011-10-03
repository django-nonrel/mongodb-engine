from django.db import models
from djangotoolbox.fields import RawField, ListField, EmbeddedModelField
from django_mongodb_engine.fields import GridFSField, GridFSString
from query.models import Post

class DescendingIndexModel(models.Model):
    desc = models.IntegerField()

    class MongoMeta:
        descending_indexes = ['desc']

class DateModel(models.Model):
    date = models.DateTimeField()

class RawModel(models.Model):
    raw = RawField()

class IndexTestModel(models.Model):
    regular_index = models.IntegerField(db_index=True)
    custom_column = models.IntegerField(db_column='foo', db_index=True)
    descending_index = models.IntegerField(db_index=True)
    descending_index_custom_column = models.IntegerField(db_column='bar', db_index=True)
    foreignkey_index = models.ForeignKey(RawModel, db_index=True)
    foreignkey_custom_column = models.ForeignKey('DateModel', db_column='spam')
    sparse_index = models.IntegerField(db_index=True)
    sparse_index_unique = models.IntegerField(db_index=True, unique=True)
    sparse_index_cmp_1 = models.IntegerField(db_index=True)
    sparse_index_cmp_2 = models.IntegerField(db_index=True)

    class MongoMeta:
        sparse_indexes = ["sparse_index", "sparse_index_unique", ('sparse_index_cmp_1', 'sparse_index_cmp_2')]
        descending_indexes = ['descending_index', 'descending_index_custom_column']
        index_together = [{ 'fields' : ['regular_index', 'custom_column']},
                          { 'fields' : ('sparse_index_cmp_1', 'sparse_index_cmp_2')}]

class IndexTestModel2(models.Model):
    a = models.IntegerField(db_index=True)
    b = models.IntegerField(db_index=True)

    class MongoMeta:
        index_together = ['a', ('b', -1)]

class NewStyleIndexesTestModel(models.Model):
    a = models.IntegerField()
    b = models.IntegerField(db_column='b2')
    c = models.IntegerField(db_index=True)
    d = models.IntegerField()
    e = models.IntegerField()
    f = models.IntegerField(unique=True)
    geo = models.IntegerField()
    geo2 = models.IntegerField(db_column='geo')

    class Meta:
        unique_together = [('a', 'b'), ('a', 'd')]

    class MongoMeta:
        indexes = [
            [('e', -1)],
            {'fields': 'a', 'sparse': True},
            {'fields': [('b', -1), 'd']},
            [('geo', '2d')],
            {'fields': [('geo2', '2d'), 'a'], 'min': 42, 'max': 21}
        ]

class GridFSFieldTestModel(models.Model):
    gridfile = GridFSField()
    gridfile_nodelete = GridFSField(delete=False)
    gridfile_versioned = GridFSField(versioning=True)
    gridfile_versioned_delete = GridFSField(versioning=True, delete=True)
    gridstring = GridFSString()

class Issue47Model(models.Model):
    foo = ListField(EmbeddedModelField(Post))

class CustomIDModel(models.Model):
    id = models.IntegerField()
    primary = models.IntegerField(primary_key=True)

class CustomIDModel2(models.Model):
    id = models.IntegerField(primary_key=True, db_column='blah')
