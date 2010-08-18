from django.db.models import signals
from .mongodb.fields import add_mongodb_manager, pre_init_mongodb_signal

signals.pre_init.connect(pre_init_mongodb_signal)
signals.class_prepared.connect(add_mongodb_manager)