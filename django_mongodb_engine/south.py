import warnings


warnings.warn(
    '`django_mongodb_engine.south.DatabaseOperations` south database backend '
    'is actually a dummy backend that does nothing at all. It will be '
    'removed in favor of the `django_mongodb_engine.south_adapter.DatabaseOperations` '
    'that provides the correct behavior.',
    DeprecationWarning
)

class DatabaseOperations(object):
    """
    MongoDB implementation of database operations.
    """

    backend_name = 'django_mongodb_engine'

    supports_foreign_keys = False
    has_check_constraints = False
    has_ddl_transactions = False

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

    def send_pending_create_signals(self, verbosity=False, interactive=False):
        pass

    def get_pending_creates(self):
        pass

    def start_transaction(self):
        pass

    def rollback_transaction(self):
        pass

    def rollback_transactions_dry_run(self):
        pass

    def clear_run_data(self, pending_creates):
        pass

    def create_table(self, unique=True, null=True, blank=True):
        pass

    def send_create_signal(self, verbosity=False, interactive=False):
        pass

    def execute_deferred_sql(self):
        pass

    def commit_transaction(self):
        pass
