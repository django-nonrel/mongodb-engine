# This is needed until the sibling south module is removed
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
        # Make sure the field is correctly prepared
        field.set_attributes_from_name(field_name)
        if field.has_default():
            default = field.get_default()
            if default is not None:
                connection = self._get_connection()
                collection = self._get_collection(table_name)
                name = field.column
                db_prep_save = field.get_db_prep_save(default, connection=connection)
                default = connection.ops.value_for_db(db_prep_save, field)
                # Update all the documents that haven't got this field yet
                collection.update({name: {'$exists': False}},
                                  {'$set': {name: default}})
            if not keep_default:
                field.default = NOT_PROVIDED

    def alter_column(self, table_name, column_name, field, explicit_name=True):
        # Since MongoDB is schemaless there's no way to coerce field datatype
        pass

    def delete_column(self, table_name, name):
        collection = self._get_collection(table_name)
        collection.update({}, {'$unset': {name: 1}})

    def rename_column(self, table_name, old, new):
        collection = self._get_collection(table_name)
        collection.update({}, {'$rename': {old: new}})

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
        # MongoDB doesn't support primary key deletion
        pass

    def create_table(self, table_name, fields, **kwargs):
        # Collection creation is automatic but code calling this might expect
        # it to exist, thus we create it here. i.e. Calls to `rename_table` will
        # fail if the collection doesn't already exist.
        connection = self._get_connection()
        connection.database.create_collection(table_name, **kwargs)
    
    def rename_table(self, table_name, new_table_name):
        collection = self._get_collection(table_name)
        collection.rename(new_table_name)

    def delete_table(self, table_name, cascade=True):
        connection = self._get_connection()
        connection.database.drop_collection(table_name)

    def start_transaction(self):
        # MongoDB doesn't support transactions
        pass

    def rollback_transaction(self):
        # MongoDB doesn't support transactions
        pass

    def commit_transaction(self):
        # MongoDB doesn't support transactions
        pass
    
    def rollback_transactions_dry_run(self):
        # MongoDB doesn't support transactions
        pass
