from django.db.models import Model

from djangotoolbox.fields import RawField


class SQLiteModel(Model):
    pass


class MongoDBModel(Model):
    # Wnsure this goes to MongoDB on syncdb: SQLite can't
    # handle RawFields.
    o = RawField()
