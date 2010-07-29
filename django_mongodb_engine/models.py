from django.db.models import signals
from django_mongodb_engine.mongodb.fields import add_mongodb_manager

signals.class_prepared.connect(add_mongodb_manager)

