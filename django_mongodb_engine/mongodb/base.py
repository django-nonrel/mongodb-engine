import pymongo

from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection

from django.core.exceptions import ImproperlyConfigured

from .creation import DatabaseCreation
from django_mongodb_engine.mongodb.operations import DatabaseOperations

class DatabaseFeatures(NonrelDatabaseFeatures):
    string_based_auto_field = True

class DatabaseClient(NonrelDatabaseClient):
    pass

class DatabaseValidation(NonrelDatabaseValidation):
    pass

class DatabaseIntrospection(NonrelDatabaseIntrospection):
    def table_names(self):
        """
        Show defined models
        """
        return self.connection.db_connection.collection_names()

    def sequence_list(self):
        # TODO: check if it's necessary to implement that
        pass

class DatabaseWrapper(NonrelDatabaseWrapper):
    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        settings_dict = self.settings_dict
        NAME = settings_dict["NAME"]
        HOST = settings_dict["HOST"]
        try:
            PORT = int(settings_dict["PORT"])
        except ValueError:
            raise ImproperlyConfigured("PORT must be an integer, or a string "
                                       "which is easily convertable to an "
                                       "integer")

        USER = settings_dict["USER"]
        PASSWORD = settings_dict["PASSWORD"]
        connection = pymongo.Connection(HOST, PORT, slave_okay=True)
        if USER and PASSWORD:
            auth = connection['admin'].authenticate(USER, PASSWORD)
            if not auth:
                raise ImproperlyConfigured("Username and/or password for \
the mongoDB are not correct")
        from .mongodb_serializer import TransformDjango
        self._connection = connection
        self.db_name = NAME
        self.db_connection = connection[NAME]
        self.db_connection.add_son_manipulator(TransformDjango())

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)
