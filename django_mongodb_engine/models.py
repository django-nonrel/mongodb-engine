from django.db.models import signals
from .mongodb.fields import add_mongodb_manager

signals.class_prepared.connect(add_mongodb_manager)