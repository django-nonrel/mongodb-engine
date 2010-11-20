from pymongo import Connection
from django.conf import settings

def get_pymongo_collection(collection):
    # TODO: How do I find out which host/port/name the test DB has?
    connection = Connection(settings.DATABASES['default']['HOST'],
                            int(settings.DATABASES['default']['PORT']))
    database = connection['test_test']
    return database[collection]

