# If you wonder what this file is about please head over to '__init__.py' :-)

from django.db.models import signals


def class_prepared_mongodb_signal(sender, *args, **kwargs):
    mongo_meta = getattr(sender, 'MongoMeta', None)
    if mongo_meta is not None:
        for attr in dir(mongo_meta):
            if not attr.startswith('_'):
                if attr == 'index_together':
                    attr_name = 'mongo_index_together'
                else:
                    attr_name = attr
                setattr(sender._meta, attr_name, getattr(mongo_meta, attr))

signals.class_prepared.connect(class_prepared_mongodb_signal)
