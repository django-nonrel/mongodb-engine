from pymongo.collection import Collection
from djangotoolbox.db.base import NonrelDatabaseCreation

TEST_DATABASE_PREFIX = 'test_'

class DatabaseCreation(NonrelDatabaseCreation):
    data_types = {
        'DateTimeField':                'datetime',
        'DateField':                    'date',
        'TimeField':                    'time',
        'FloatField':                   'float',
        'EmailField':                   'unicode',
        'URLField':                     'unicode',
        'BooleanField':                 'bool',
        'NullBooleanField':             'bool',
        'CharField':                    'unicode',
        'CommaSeparatedIntegerField':   'unicode',
        'IPAddressField':               'unicode',
        'SlugField':                    'unicode',
        'FileField':                    'unicode',
        'FilePathField':                'unicode',
        'TextField':                    'unicode',
        'XMLField':                     'unicode',
        'IntegerField':                 'int',
        'SmallIntegerField':            'int',
        'PositiveIntegerField':         'int',
        'PositiveSmallIntegerField':    'int',
        'BigIntegerField':              'int',
        'GenericAutoField':             'objectid',
        'StringForeignKey':             'objectid',
        'AutoField':                    'objectid',
        'RelatedAutoField':             'objectid',
        'OneToOneField':                'int',
        'DecimalField':                 'float',
    }

    def sql_indexes_for_field(self, model, f, style):
        if f.db_index:
            kwargs = {}
            opts = model._meta
            col = getattr(self.connection.db_connection, opts.db_table)
            descending = getattr(model._meta, "descending_indexes", [])
            direction =  (f.attname in descending and -1) or 1
            kwargs["unique"] = f.unique
            col.ensure_index([(f.name, direction)], **kwargs)
        return []

    def index_fields_group(self, model, group, style):
        if not isinstance(group, dict):
            raise TypeError, "Indexes group has to be instance of dict"

        fields = group.pop("fields")

        if not isinstance(fields, (list, tuple)):
            raise TypeError, "index_together fields has to be instance of list"

        opts = model._meta
        col = getattr(self.connection.db_connection, opts.db_table)
        checked_fields = []
        model_fields = [ f.name for f in opts.local_fields]

        for field in fields:
            field_name = field
            direction = 1
            if isinstance(field, (tuple,list)):
                field_name = field[0]
                direction = (field[1] and 1) or -1
            if not field_name in model_fields:
                from django.db.models.fields import FieldDoesNotExist
                raise FieldDoesNotExist('%s has no field named %r' % (opts.object_name, field_name))
            checked_fields.append((field_name, direction))
        col.ensure_index(checked_fields, **group)
            
    def sql_indexes_for_model(self, model, style):
        "Returns the CREATE INDEX SQL statements for a single model"
        if not model._meta.managed or model._meta.proxy:
            return []
        fields = [ f for f in model._meta.local_fields if f.db_index]
        if not fields and not hasattr(model._meta, "index_together") and not hasattr(model._meta, "unique_together"):
            return []
        print "Installing index for %s.%s model" % (model._meta.app_label, model._meta.object_name)
        for f in fields:
            self.sql_indexes_for_field(model, f, style)
        for group in getattr(model._meta, "index_together", []):
            self.index_fields_group(model, group, style)
        
        #unique_together support
        unique_together = getattr(model._meta, "unique_together", [])
        # Django should do this, I just wanted to be REALLY sure.
        if len(unique_together) > 0 and isinstance(unique_together[0], basestring):
            unique_together = (unique_together,)
        for fields in unique_together:
            group = { "fields" : fields,
                      "unique" : True
                      }
            self.index_fields_group(model, group, style)
        return []

    def sql_create_model(self, model, style, known_models=set()):
        opts = model._meta
        kwargs = {}
        kwargs["capped"] = getattr(opts, "capped", False)
        if hasattr(opts, "collection_max") and opts.collection_max:
            kwargs["max"] = opts.collection_max
        if hasattr(opts, "collection_size") and opts.collection_size:
            kwargs["size"] = opts.collection_size
        col = Collection(self.connection.db_connection, model._meta.db_table, **kwargs)
        return [], {}

    def set_autocommit(self):
        "Make sure a connection is in autocommit mode."
        pass

    def create_test_db(self, verbosity=1, autoclobber=False):
        # No need to create databases in mongoDB :)
        # but we can make sure that if the database existed is emptied
        from django.conf import settings
        if self.connection.settings_dict.get('TEST_NAME'):
            test_database_name = self.connection.settings_dict['TEST_NAME']
        elif 'NAME' in self.connection.settings_dict:
            test_database_name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
        elif 'DATABASE_NAME' in self.connection.settings_dict:
            if self.connection.settings_dict['DATABASE_NAME'].startswith(TEST_DATABASE_PREFIX):
                # already been set up
                # must be because this is called from a setUp() instead of something formal.
                # suspect this Django 1.1
                test_database_name = self.connection.settings_dict['DATABASE_NAME']
            else:
                test_database_name = TEST_DATABASE_PREFIX + \
                  self.connection.settings_dict['DATABASE_NAME']
        else:
            raise ValueError("Name for test database not defined")
        
        self.connection.settings_dict['NAME'] = test_database_name
        # This is important. Here we change the settings so that all other code
        # things that the chosen database is now the test database. This means
        # that nothing needs to change in the test code for working with 
        # connections, databases and collections. It will appear the same as
        # when working with non-test code.
        
        # In this phase it will only drop the database if it already existed
        # which could potentially happen if the test database was created but 
        # was never dropped at the end of the tests
        self._drop_database(test_database_name)
        
    def destroy_test_db(self, old_database_name, verbosity=1):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        """
        if verbosity >= 1:
            print "Destroying test database '%s'..." % self.connection.alias
        test_database_name = self.connection.settings_dict['NAME']
        self._drop_database(test_database_name)
        self.connection.settings_dict['NAME'] = old_database_name
        
    def _drop_database(self, database_name):
        self.connection._cursor().drop_database(database_name)
        
