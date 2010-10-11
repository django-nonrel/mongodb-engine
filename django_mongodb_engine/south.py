class DatabaseOperations(object):
    """
    MongoDB implementation of database operations.
    """

    backend_name = 'django_mongodb_engine'

    supports_foreign_keys = False
    has_check_constraints = False

    def __init__(self, db_alias):
        pass

    def add_column(self, table_name, name, field, *args, **kwds):
        pass

    def alter_column(self, table_name, name, field, explicit_name=True):
        pass

    def delete_column(self, table_name, column_name):
        pass

    def rename_column(self, table_name, old, new):
        pass

    def create_unique(self, table_name, columns):
        pass

    def delete_unique(self, table_name, columns):
        pass

    def delete_primary_key(self, table_name):
        pass

    def delete_table(self, table_name, cascade=True):
        pass

    def connection_init(self):
        pass
