from django.db import models
from djangotoolbox.fields import ListField, DictField, EmbeddedModelField
from django_mongodb_engine.contrib import MongoDBManager


class DotQueryForeignModel(models.Model):
    f_char = models.CharField(max_length=200, db_column='dbc_char')


class DotQueryEmbeddedModel(models.Model):
    f_int = models.IntegerField(db_column='dbc_int')
    f_foreign = models.ForeignKey(
        DotQueryForeignModel,
        null=True,
        blank=True,
        db_column='dbc_foreign'
    )


class DotQueryTestModel(models.Model):
    objects = MongoDBManager()

    f_id = models.IntegerField()
    f_dict = DictField(db_column='dbc_dict')
    f_list = ListField(db_column='dbc_list')
    f_embedded = EmbeddedModelField(
        DotQueryEmbeddedModel,
        db_column='dbc_embedded',
    )
    f_embedded_list = ListField(
        EmbeddedModelField(
            DotQueryEmbeddedModel,
            db_column='dbc_embedded',
        ),
        db_column='dbc_embedded_list',
    )
