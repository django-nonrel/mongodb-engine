from django.conf import settings
from django.db import connections

def get_databases():
    default_database = None
    databases = []
    for name, databaseopt in settings.DATABASES.iteritems():
        if databaseopt['ENGINE'] == 'django_mongodb_engine':
            databases.append(name)
            if databaseopt.get('IS_DEFAULT'):
                if default_database is None:
                    default_database = name
                else:
                    raise ImproperlyConfigured("There can be only one default MongoDB database")

    if not databases:
        raise ImproperlyConfigured("No MongoDB database found in settings.DATABASES")

    if default_database is None:
        default_database = databases[0]

    return default_database, databases
    
def get_default_database():
    return get_databases()[0]
    
def get_default_db_connection():
    return connections[get_default_database()].db_connection