from django.db import models

def class_prepared_mongodb_signal(sender, *args, **kwargs):
    mongo_meta = getattr(sender, 'MongoMeta', None)
    if mongo_meta is not None:
        for attr in dir(mongo_meta):
            if not attr.startswith('_'):
                setattr(sender._meta, attr, getattr(mongo_meta, attr))

models.signals.class_prepared.connect(class_prepared_mongodb_signal)
