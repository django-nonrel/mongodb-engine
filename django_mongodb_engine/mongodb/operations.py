from djangotoolbox.db.base import NonrelDatabaseOperations

class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def sql_flush(self, style, tables, sequence_list):
        tables = self.connection.db_connection.collection_names()
        tables = [name for name in tables if not name.startswith('system.')]
        for table in tables:
            self.connection.db_connection.drop_collection(table)
        return []

    def check_aggregate_support(self, aggregate):
        """
        This function is meant to raise exception if backend does
        not support aggregation.

        In fact, mongo probably even has more flexible aggregation
        support than relational DB
        """
        pass