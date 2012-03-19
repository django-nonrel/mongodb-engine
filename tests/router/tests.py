from django.db.utils import DatabaseError
from django.test import TestCase


class RouterTest(TestCase):

    def test_managed_apps(self):
        # MONGODB_MANAGED_APPS = ['query'] : Any 'query' model resides
        # in the MongoDB 'other'.
        from query.models import Blog
        Blog.objects.create()
        self.assertEqual(Blog.objects.using('other').count(), 1)
        self.assertRaisesRegexp(DatabaseError, "no such table",
            Blog.objects.using('default').count)

    def test_managed_models(self):
        # MONGODB_MANAGED_MODELS = ['router.MongoDBModel']:
        # router.models.MongoDBModel resides in MongoDB,
        # .SQLiteModel in SQLite.
        from router.models import MongoDBModel, SQLiteModel
        mongo_obj = MongoDBModel.objects.create()
        sql_obj = SQLiteModel.objects.create()

        self.assertEqual(MongoDBModel.objects.get(), mongo_obj)
        self.assertEqual(SQLiteModel.objects.get(), sql_obj)

        self.assertEqual(MongoDBModel.objects.using('other').get(), mongo_obj)
        self.assertEqual(SQLiteModel.objects.using('default').get(), sql_obj)

        self.assertEqual(SQLiteModel.objects.using('other').count(), 0)
        self.assertRaisesRegexp(DatabaseError, "no such table",
                                MongoDBModel.objects.using('default').count)
