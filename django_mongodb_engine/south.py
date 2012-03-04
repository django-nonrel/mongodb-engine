# What a great idea it was to name this module south...
# TODO: This module should be renamed to south_adapter
from __future__ import absolute_import 

from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields import NOT_PROVIDED
from django.db.utils import IntegrityError
from pymongo.errors import DuplicateKeyError

from .utils import make_index_list


try:
    from south.db.generic import DatabaseOperations
except ImportError:
    raise ImproperlyConfigured('Make sure to install south before trying to '
                               'import this module.')


class DatabaseOperations(DatabaseOperations):
    """
    MongoDB implementation of database operations.
    """

    backend_name = 'django_mongodb_engine'

    supports_foreign_keys = False
    has_check_constraints = False
    has_ddl_transactions = False

    def _get_collection(self, name):
        return self._get_connection().get_collection(name)

    def add_column(self, table_name, field_name, field, keep_default=True):
        collection = self._get_collection(table_name)
        __, name = field.get_attname_column()
        if field.default is not NOT_PROVIDED:
            default = field.default() if callable(field.default) else field.default
            # Update all the documents that have not this field yet
            collection.update({name: {'$exists': False}}, {'$set': {name: default}})
            if not keep_default:
                field.default = NOT_PROVIDED

    def alter_column(self, table_name, column_name, field, explicit_name=True):
        # There's not much we can do here
        pass

    def delete_column(self, table_name, name):
        collection = self._get_collection(table_name)
        collection.update(dict(), {'$unset': {name: 1}})

    def rename_column(self, table_name, old, new):
        collection = self._get_collection(table_name)
        collection.update(dict(), {'$rename': {old: new}})

    def create_unique(self, table_name, columns, drop_dups=False):
        collection = self._get_collection(table_name)
        try:
            index_list = list(make_index_list(columns))
            collection.create_index(index_list, unique=True, drop_dups=drop_dups)
        except DuplicateKeyError as e:
            raise IntegrityError(e)

    def delete_unique(self, table_name, columns):
        collection = self._get_collection(table_name)
        index_list = list(make_index_list(columns))
        collection.drop_index(index_list)

    def delete_primary_key(self, table_name):
        pass

    def create_table(self, table_name, fields, **kwargs):
        # Collection creation is automatic but code calling this might expect
        # it to exist, thus we create it here.
        connection = self._get_connection()
        connection.database.create_collection(table_name, **kwargs)
    
    def rename_table(self, table_name, new_table_name):
        collection = self._get_collection(table_name)
        collection.rename(new_table_name)

    def delete_table(self, table_name, cascade=True):
        connection = self._get_connection()
        connection.database.drop_collection(table_name)

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

    def send_create_signal(self, verbosity=False, interactive=False):
        pass

    def execute_deferred_sql(self):
        pass

    def commit_transaction(self):
        pass
