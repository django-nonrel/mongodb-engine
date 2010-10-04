from django.conf import settings
from django.db.models import signals
from .mongodb.fields import add_mongodb_manager, pre_init_mongodb_signal

if 'django_mongodb_engine' not in settings.INSTALLED_APPS:
    settings.INSTALLED_APPS.insert(0, 'django_mongodb_engine')

signals.pre_init.connect(pre_init_mongodb_signal)
signals.class_prepared.connect(add_mongodb_manager)
