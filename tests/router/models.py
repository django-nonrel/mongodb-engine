from django.db.models import Model

class SQLiteModel(Model):
    pass

from djangotoolbox.fields import RawField
class MongoDBModel(Model):
    # ensure this goes to MongoDB on syncdb: SQLite can't handle RawFields.
    o = RawField()
