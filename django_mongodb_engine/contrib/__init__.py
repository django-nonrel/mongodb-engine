from django.db import models
from mapreduce import MapReduceMixin

class MongoDBManager(models.Manager, MapReduceMixin):
    pass
