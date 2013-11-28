from django.db.utils import DatabaseError

from pymongo import DESCENDING

from djangotoolbox.db.creation import NonrelDatabaseCreation

from .utils import make_index_list


class DatabaseCreation(NonrelDatabaseCreation):

    # We'll store decimals as strings, dates and times as datetimes,
    # sets as lists and automatic keys as ObjectIds.
    data_types = dict(NonrelDatabaseCreation.data_types, **{
        'SetField': 'list',
    })

    def db_type(self, field):
        """
        Returns the db_type of the field for non-relation fields, and
        the db_type of a primary key field of a related model for
        ForeignKeys, OneToOneFields and ManyToManyFields.
        """
        if field.rel is not None:
            field = field.rel.get_related_field()
        return field.db_type(connection=self.connection)

    def sql_indexes_for_model(self, model, termstyle):
        """Creates indexes for all fields in ``model``."""
        meta = model._meta

        if not meta.managed or meta.proxy:
            return []

        collection = self.connection.get_collection(meta.db_table)

        def ensure_index(*args, **kwargs):
            if ensure_index.first_index:
                print "Installing indices for %s.%s model." % \
                      (meta.app_label, meta.object_name)
                ensure_index.first_index = False
            return collection.ensure_index(*args, **kwargs)
        ensure_index.first_index = True

        newstyle_indexes = getattr(meta, 'indexes', None)
        if newstyle_indexes:
            self._handle_newstyle_indexes(ensure_index, meta, newstyle_indexes)
        else:
            self._handle_oldstyle_indexes(ensure_index, meta)

    def _handle_newstyle_indexes(self, ensure_index, meta, indexes):
        from djangotoolbox.fields import AbstractIterableField, \
            EmbeddedModelField

        # Django indexes.
        for field in meta.local_fields:
            if not (field.unique or field.db_index):
                # field doesn't need an index.
                continue
            column = '_id' if field.primary_key else field.column
            ensure_index(column, unique=field.unique)

        # Django unique_together indexes.
        indexes = list(indexes)

        for fields in getattr(meta, 'unique_together', []):
            assert isinstance(fields, (list, tuple))
            indexes.append({'fields': make_index_list(fields), 'unique': True})

        def get_column_name(field):
            opts = meta
            parts = field.split('.')
            for i, part in enumerate(parts):
                field = opts.get_field(part)
                parts[i] = field.column
                if isinstance(field, AbstractIterableField):
                    field = field.item_field
                if isinstance(field, EmbeddedModelField):
                    opts = field.embedded_model._meta
                else:
                    break
            return '.'.join(parts)

        for index in indexes:
            if isinstance(index, dict):
                kwargs = index.copy()
                fields = kwargs.pop('fields')
            else:
                fields, kwargs = index, {}
            fields = [(get_column_name(name), direction)
                      for name, direction in make_index_list(fields)]
            ensure_index(fields, **kwargs)

    def _handle_oldstyle_indexes(self, ensure_index, meta):
        from warnings import warn
        warn("'descending_indexes', 'sparse_indexes' and 'index_together' "
             "are deprecated and will be ignored as of version 0.6. "
             "Use 'indexes' instead.", DeprecationWarning)
        sparse_indexes = []
        descending_indexes = set(getattr(meta, 'descending_indexes', ()))

        # Lets normalize the sparse_index values changing [], set() to ().
        for idx in set(getattr(meta, 'sparse_indexes', ())):
            sparse_indexes.append(
                isinstance(idx, (tuple, set, list)) and tuple(idx) or idx)

        # Ordinary indexes.
        for field in meta.local_fields:
            if not (field.unique or field.db_index):
                # field doesn't need an index.
                continue
            column = '_id' if field.primary_key else field.column
            if field.name in descending_indexes:
                column = [(column, DESCENDING)]
            ensure_index(column, unique=field.unique,
                         sparse=field.name in sparse_indexes)

        def create_compound_indexes(indexes, **kwargs):
            # indexes: (field1, field2, ...).
            if not indexes:
                return
            kwargs['sparse'] = tuple(indexes) in sparse_indexes
            indexes = [(meta.get_field(name).column, direction) for
                       name, direction in make_index_list(indexes)]
            ensure_index(indexes, **kwargs)

        # Django unique_together indexes.
        for indexes in getattr(meta, 'unique_together', []):
            assert isinstance(indexes, (list, tuple))
            create_compound_indexes(indexes, unique=True)

        # MongoDB compound indexes.
        index_together = getattr(meta, 'mongo_index_together', [])
        if index_together:
            if isinstance(index_together[0], dict):
                # Assume index_together = [{'fields' : [...], ...}].
                for args in index_together:
                    kwargs = args.copy()
                    create_compound_indexes(kwargs.pop('fields'), **kwargs)
            else:
                # Assume index_together = ['foo', 'bar', ('spam', -1), etc].
                create_compound_indexes(index_together)

        return []

    def sql_create_model(self, model, *unused):
        """
        Creates a collection that will store instances of the model.

        Technically we only need to precreate capped collections, but
        we'll create them for all models, so database introspection
        knows about empty "tables".
        """
        name = model._meta.db_table
        if getattr(model._meta, 'capped', False):
            kwargs = {'capped': True}
            size = getattr(model._meta, 'collection_size', None)
            if size is not None:
                kwargs['size'] = size
            max_ = getattr(model._meta, 'collection_max', None)
            if max_ is not None:
                kwargs['max'] = max_
        else:
            kwargs = {}

        collection = self.connection.get_collection(name, existing=True)
        if collection is not None:
            opts = dict(collection.options())
            if opts != kwargs:
                raise DatabaseError("Can't change options of an existing "
                                    "collection: %s --> %s." % (opts, kwargs))

        # Initialize the capped collection:
        self.connection.get_collection(name, **kwargs)

        return [], {}

    def set_autocommit(self):
        """There's no such thing in MongoDB."""

    def create_test_db(self, verbosity=1, autoclobber=False):
        """
        No need to create databases in MongoDB :)
        but we can make sure that if the database existed is emptied.
        """
        test_database_name = self._get_test_db_name()

        self.connection.settings_dict['NAME'] = test_database_name
        # This is important. Here we change the settings so that all
        # other code thinks that the chosen database is now the test
        # database. This means that nothing needs to change in the test
        # code for working with connections, databases and collections.
        # It will appear the same as when working with non-test code.

        # Force a reconnect to ensure we're using the test database.
        self.connection._reconnect()

        # In this phase it will only drop the database if it already
        # existed which could potentially happen if the test database
        # was created but was never dropped at the end of the tests.
        self._drop_database(test_database_name)

        from django.core.management import call_command
        call_command('syncdb', verbosity=max(verbosity-1, 0),
                     interactive=False, database=self.connection.alias)

        return test_database_name

    def destroy_test_db(self, old_database_name, verbosity=1):
        if verbosity >= 1:
            print "Destroying test database for alias '%s'..." % \
                  self.connection.alias
        test_database_name = self.connection.settings_dict['NAME']
        self._drop_database(test_database_name)
        self.connection.settings_dict['NAME'] = old_database_name

    def _drop_database(self, database_name):
        for collection in self.connection.introspection.table_names():
            if not collection.startswith('system.'):
                self.connection.database.drop_collection(collection)
