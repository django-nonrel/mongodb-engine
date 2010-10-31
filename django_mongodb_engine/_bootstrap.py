from django.db import models

def class_prepared_mongodb_signal(sender, *args, **kwargs):
    mongo_meta = getattr(sender, 'MongoMeta', None)
    if mongo_meta is not None:
        for attr, value in mongo_meta.items():
            if not attr.startswith('_'):
                setattr(sender._meta, attr, value)

models.signals.class_prepared.connect(class_prepared_mongodb_signal)
