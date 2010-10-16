try:
    from django import MODIFIED as modified_django
except ImportError:
    modified_django = False
from django.core import exceptions
from django.conf import settings
from django.db import models
from django.db.models.fields import AutoField as DjangoAutoField
from pymongo.objectid import ObjectId

class MongoMeta(object):
    pass

def class_prepared_mongodb_signal(sender, *args, **kwargs):
    model = sender
    mongo_meta = getattr(cls, "MongoMeta", MongoMeta).__dict__.copy()
    for attr in mongo_meta:
        if attr.startswith("_"):
            continue
        setattr(model._meta, attr, mongo_meta[attr])

models.signals.class_prepared.connect(class_prepared_mongodb_signal)
