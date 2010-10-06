from djangotoolbox.db.base import NonrelDatabaseOperations

class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def max_name_length(self):
        return 254

    def sql_flush(self, style, tables, sequence_list):
        tables = self.connection.db_connection.collection_names()
        tables = [name for name in tables if not name.startswith('system.')]
        for table in tables:
            self.connection.db_connection.drop_collection(table)
        return []

    def check_aggregate_support(self, aggregate):
        """
        Returns whether the database supports aggregations of type ``aggregate``.
        """
        from django.db.models.sql.aggregates import Count
        return isinstance(aggregate, Count) # MongoDB only supports Counts
