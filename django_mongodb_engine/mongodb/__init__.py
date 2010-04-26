from django.db.models import signals

from fields import add_mongodb_manager 

signals.class_prepared.connect(add_mongodb_manager)
