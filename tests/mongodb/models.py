from django.db import models

from djangotoolbox.fields import RawField, ListField, DictField, \
    EmbeddedModelField

from django_mongodb_engine.fields import GridFSField, GridFSString

# ensures class_prepared signal handler is installed
from django_mongodb_engine import models as mongo_models

from query.models import Post


class DescendingIndexModel(models.Model):
    desc = models.IntegerField()

    class MongoMeta:
        descending_indexes = ['desc']


class DateModel(models.Model):
    date = models.DateField()


class DateTimeModel(models.Model):
    datetime = models.DateTimeField()


class RawModel(models.Model):
    raw = RawField()


class IndexTestModel(models.Model):
    regular_index = models.IntegerField(db_index=True)
    custom_column = models.IntegerField(db_column='foo', db_index=True)
    descending_index = models.IntegerField(db_index=True)
    descending_index_custom_column = models.IntegerField(db_column='bar',
                                                         db_index=True)
    foreignkey_index = models.ForeignKey(RawModel, db_index=True, on_delete=models.DO_NOTHING)
    foreignkey_custom_column = models.ForeignKey('DateModel',
                                                 db_column='spam')
    sparse_index = models.IntegerField(db_index=True)
    sparse_index_unique = models.IntegerField(db_index=True, unique=True)
    sparse_index_cmp_1 = models.IntegerField(db_index=True)
    sparse_index_cmp_2 = models.IntegerField(db_index=True)

    class MongoMeta:
        sparse_indexes = ['sparse_index', 'sparse_index_unique',
                          ('sparse_index_cmp_1', 'sparse_index_cmp_2')]
        descending_indexes = ['descending_index',
                              'descending_index_custom_column']
        index_together = [
            {'fields': ['regular_index', 'custom_column']},
            {'fields': ('sparse_index_cmp_1', 'sparse_index_cmp_2')}]


class IndexTestModel2(models.Model):
    a = models.IntegerField(db_index=True)
    b = models.IntegerField(db_index=True)

    class MongoMeta:
        index_together = ['a', ('b', -1)]


class CustomColumnEmbeddedModel(models.Model):
    a = models.IntegerField(db_column='a2')


class NewStyleIndexesTestModel(models.Model):
    f1 = models.IntegerField()
    f2 = models.IntegerField()
    f3 = models.IntegerField()

    db_index = models.IntegerField(db_index=True)
    unique = models.IntegerField(unique=True)
    custom_column = models.IntegerField(db_column='custom')
    geo = models.IntegerField()
    geo_custom_column = models.IntegerField(db_column='geo')

    dict1 = DictField()
    dict_custom_column = DictField(db_column='dict_custom')
    embedded = EmbeddedModelField(CustomColumnEmbeddedModel)
    embedded_list = ListField(EmbeddedModelField(CustomColumnEmbeddedModel))

    class Meta:
        unique_together = [('f2', 'custom_column'), ('f2', 'f3')]

    class MongoMeta:
        indexes = [
            [('f1', -1)],
            {'fields': 'f2', 'sparse': True},
            {'fields': [('custom_column', -1), 'f3']},
            [('geo', '2d')],
            {'fields': [('geo_custom_column', '2d'), 'f2'],
             'min': 42, 'max': 21},
            {'fields': [('dict1.foo', 1)]},
            {'fields': [('dict_custom_column.foo', 1)]},
            {'fields': [('embedded.a', 1)]},
            {'fields': [('embedded_list.a', 1)]},
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


class CappedCollection(models.Model):
    n = models.IntegerField(default=42)

    class MongoMeta:
        capped = True
        collection_size = 10


class CappedCollection2(models.Model):

    class MongoMeta:
        capped = True
        collection_size = 1000
        collection_max = 2


class CappedCollection3(models.Model):
    n = models.IntegerField(default=43)

    class MongoMeta:
        capped = True
        collection_size = 1000
