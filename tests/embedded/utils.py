from pymongo import Connection
from django.conf import settings

def get_pymongo_collection(collection):
    connection = Connection(settings.DATABASES['default']['HOST'] or settings.DATABASES['mongodb']['HOST'])
    database = connection['test_test']
    return database[collection]

