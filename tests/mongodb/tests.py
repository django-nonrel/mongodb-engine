from __future__ import with_statement
from cStringIO import StringIO

from django.core.management import call_command
from django.contrib.sites.models import Site
from django.db import connection, connections
from django.db.utils import DatabaseError, IntegrityError
from django.db.models import Q

from gridfs import GridOut
from pymongo import ASCENDING, DESCENDING

from django_mongodb_engine.base import DatabaseWrapper

from models import *
from utils import *


class MongoDBEngineTests(TestCase):
    """Tests for mongodb-engine specific features."""

    def test_mongometa(self):
        self.assertEqual(DescendingIndexModel._meta.descending_indexes,
                        ['desc'])

    def test_A_query(self):
        from django_mongodb_engine.query import A
        obj1 = RawModel.objects.create(raw=[{'a': 1, 'b': 2}])
        obj2 = RawModel.objects.create(raw=[{'a': 1, 'b': 3}])
        self.assertEqualLists(RawModel.objects.filter(raw=A('a', 1)),
                              [obj1, obj2])
        self.assertEqual(RawModel.objects.get(raw=A('b', 2)), obj1)
        self.assertEqual(RawModel.objects.get(raw=A('b', 3)), obj2)

    def test_nice_monthday_query_exception(self):
        with self.assertRaisesRegexp(DatabaseError, "not support month/day"):
            DateModel.objects.get(date__month=1)
        with self.assertRaisesRegexp(DatabaseError, "not support month/day"):
            len(DateTimeModel.objects.filter(datetime__day=1))

    def test_nice_int_objectid_exception(self):
        msg = "AutoField \(default primary key\) values must be strings " \
              "representing an ObjectId on MongoDB \(got u?'%s' instead\)."
        self.assertRaisesRegexp(
                DatabaseError, msg % u'helloworld...',
                RawModel.objects.create, id='helloworldwhatsup')
        self.assertRaisesRegexp(
            DatabaseError, (msg % '5') +
                " Please make sure your SITE_ID contains a valid ObjectId string.",
            Site.objects.get, id='5')

    def test_generic_field(self):
        for obj in [['foo'], {'bar': 'buzz'}]:
            id = RawModel.objects.create(raw=obj).id
            self.assertEqual(RawModel.objects.get(id=id).raw, obj)

    def test_databasewrapper_api(self):
        from pymongo.mongo_client import MongoClient
        from pymongo.database import Database
        from pymongo.collection import Collection
        from random import shuffle

        if settings.DEBUG:
            from django_mongodb_engine.utils import \
                CollectionDebugWrapper as Collection

        for wrapper in [connection,
                        DatabaseWrapper(connection.settings_dict)]:
            calls = [
                lambda: self.assertIsInstance(wrapper.get_collection('foo'),
                                              Collection),
                lambda: self.assertIsInstance(wrapper.database, Database),
                lambda: self.assertIsInstance(wrapper.connection, MongoClient),
            ]
            shuffle(calls)
            for call in calls:
                call()

    def test_tellsiteid(self):
        from django.contrib.sites.models import Site
        site_id = Site.objects.create().id
        for kwargs in [{}, {'verbosity': 1}]:
            stdout = StringIO()
            call_command('tellsiteid', stdout=stdout, **kwargs)
            self.assertIn(site_id, stdout.getvalue())


class RegressionTests(TestCase):
    def test_djangononrel_issue_8(self):
        """
        ForeignKeys should be ObjectIds, not unicode.
        """
        from bson.objectid import ObjectId
        from query.models import Blog, Post

        post = Post.objects.create(blog=Blog.objects.create())
        collection = get_collection(Post)
        assert collection.count() == 1
        doc = collection.find_one()
        self.assertIsInstance(doc['blog_id'], ObjectId)

    def test_issue_47(self):
        """
        ForeignKeys in subobjects should be ObjectIds, not unicode.
        """
        # handle pymongo backward compatibility
        try:
            from bson.objectid import ObjectId
        except ImportError:
            from pymongo.objectid import ObjectId
        from query.models import Blog, Post
        post = Post.objects.create(blog=Blog.objects.create())
        Issue47Model.objects.create(foo=[post])
        collection = get_collection(Issue47Model)
        assert collection.count() == 1
        doc = collection.find_one()
        self.assertIsInstance(doc['foo'][0]['blog_id'], ObjectId)

    def test_djangotoolbox_issue_7(self):
        """Subobjects should not have an id field."""
        from query.models import Post
        Issue47Model.objects.create(foo=[Post(title='a')])
        collection = get_collection(Issue47Model)
        assert collection.count() == 1
        doc = collection.find_one()
        self.assertNotIn('id', doc['foo'][0])

    def test_custom_id_field(self):
        """Everything should work fine with custom primary keys."""
        CustomIDModel.objects.create(id=42, primary=666)
        self.assertDictContainsSubset(
            {'_id': 666, 'id': 42},
            get_collection(CustomIDModel).find_one())
        CustomIDModel2.objects.create(id=42)
        self.assertDictContainsSubset(
            {'_id': 42},
            get_collection(CustomIDModel2).find_one())
        obj = CustomIDModel2.objects.create(id=41)
        self.assertEqualLists(
            CustomIDModel2.objects.order_by('id').values('id'),
            [{'id': 41}, {'id': 42}])
        self.assertEqualLists(
            CustomIDModel2.objects.order_by('-id').values('id'),
            [{'id': 42}, {'id': 41}])
        self.assertEqual(obj, CustomIDModel2.objects.get(id=41))

    def test_multiple_exclude(self):
        objs = [RawModel.objects.create(raw=i) for i in xrange(1, 6)]
        self.assertEqual(
            objs[-1],
            RawModel.objects.exclude(raw=1).exclude(raw=2)
                            .exclude(raw=3).exclude(raw=4).get())
        list(RawModel.objects.filter(raw=1).filter(raw=2))
        list(RawModel.objects.filter(raw=1).filter(raw=2)
                             .exclude(raw=3))
        list(RawModel.objects.filter(raw=1).filter(raw=2)
                             .exclude(raw=3).exclude(raw=4))
        list(RawModel.objects.filter(raw=1).filter(raw=2)
                             .exclude(raw=3).exclude(raw=4).filter(raw=5))

    def test_multiple_exclude_random(self):
        from random import randint

        for i in xrange(20):
            RawModel.objects.create(raw=i)

        for i in xrange(10):
            q = RawModel.objects.all()
            for i in xrange(randint(0, 20)):
                q = getattr(q, 'filter' if randint(0, 1) else 'exclude')(raw=i)
            list(q)

    def test_issue_89(self):
        query = [Q(raw='a') | Q(raw='b'),
                 Q(raw='c') | Q(raw='d')]
        self.assertRaises(AssertionError, RawModel.objects.get, *query)


class DatabaseOptionTests(TestCase):
    """Tests for MongoDB-specific database options."""

    class custom_database_wrapper(object):

        def __init__(self, settings, **kwargs):
            self.new_wrapper = DatabaseWrapper(
                dict(connection.settings_dict, **settings),
                **kwargs)

        def __enter__(self):
            self._old_connection = getattr(connections._connections, 'default')
            connections._connections.default = self.new_wrapper
            self.new_wrapper._connect()
            return self.new_wrapper

        def __exit__(self, *exc_info):
            self.new_wrapper.connection.disconnect()
            connections._connections.default = self._old_connection

    def test_pymongo_connection_args(self):

        class foodict(dict):
            pass

        with self.custom_database_wrapper({
                'OPTIONS': {
                    'SLAVE_OKAY': True,
                    'TZ_AWARE': True,
                    'DOCUMENT_CLASS': foodict,
                }}) as connection:
            for name, value in connection.settings_dict[
                    'OPTIONS'].iteritems():
                name = '_Connection__%s' % name.lower()
                if name not in connection.connection.__dict__:
                    # slave_okay was moved into BaseObject in PyMongo 2.0.
                    name = name.replace('Connection', 'BaseObject')
                if name not in connection.connection.__dict__:
                    # document_class was moved into MongoClient in PyMongo 2.4.
                    name = name.replace('BaseObject', 'MongoClient')
                self.assertEqual(connection.connection.__dict__[name], value)

    def test_operation_flags(self):
        def test_setup(flags, **method_kwargs):
            cls_code = [
                'from pymongo.collection import Collection',
                'class Collection(Collection):',
                '    _method_kwargs = {}',
            ]
            for name in method_kwargs:
                for line in [
                    'def %s(self, *args, **kwargs):',
                    '    assert %r not in self._method_kwargs',
                    '    self._method_kwargs[%r] = kwargs',
                    '    return super(self.__class__, self).%s(*args, **kwargs)\n',
                ]:
                    cls_code.append('    ' + line % name)

            exec '\n'.join(cls_code) in locals()

            options = {'OPTIONS': {'OPERATIONS': flags}}
            with self.custom_database_wrapper(options,
                                              collection_class=Collection):
                RawModel.objects.create(raw='foo')
                update_count = RawModel.objects.update(raw='foo'), \
                               RawModel.objects.count()
                RawModel.objects.all().delete()

            for name in method_kwargs:
                self.assertEqual(method_kwargs[name],
                                 Collection._method_kwargs[name])

            if Collection._method_kwargs['update'].get('safe'):
                self.assertEqual(*update_count)

        test_setup({}, save={}, update={'multi': True}, remove={})
        test_setup({
            'safe': True},
            save={'safe': True},
            update={'safe': True, 'multi': True},
            remove={'safe': True})
        test_setup({
            'delete': {'safe': True}, 'update': {}},
            save={},
            update={'multi': True},
            remove={'safe': True})
        test_setup({
            'insert': {'fsync': True}, 'delete': {'fsync': True}},
            save={},
            update={'multi': True},
            remove={'fsync': True})

    def test_unique(self):
        with self.custom_database_wrapper({'OPTIONS': {}}):
            Post.objects.create(title='a', content='x')
            Post.objects.create(title='a', content='y')
            self.assertEqual(Post.objects.count(), 1)
            self.assertEqual(Post.objects.get().content, 'x')

    def test_unique_safe(self):
        Post.objects.create(title='a')
        self.assertRaises(IntegrityError, Post.objects.create, title='a')


class IndexTests(TestCase):

    def assertHaveIndex(self, field_name, direction=ASCENDING):
        info = get_collection(IndexTestModel).index_information()
        index_name = field_name + ['_1', '_-1'][direction == DESCENDING]
        self.assertIn(index_name, info)
        self.assertIn((field_name, direction), info[index_name]['key'])

    # Assumes fields as [(name, direction), (name, direction)].
    def assertCompoundIndex(self, fields, model=IndexTestModel):
        info = get_collection(model).index_information()
        index_names = [field[0] + ['_1', '_-1'][field[1] == DESCENDING]
                       for field in fields]
        index_name = '_'.join(index_names)
        self.assertIn(index_name, info)
        self.assertEqual(fields, info[index_name]['key'])

    def assertIndexProperty(self, field_name, name, direction=ASCENDING):
        info = get_collection(IndexTestModel).index_information()
        index_name = field_name + ['_1', '_-1'][direction == DESCENDING]
        self.assertTrue(info.get(index_name, {}).get(name, False))

    def test_regular_indexes(self):
        self.assertHaveIndex('regular_index')

    def test_custom_columns(self):
        self.assertHaveIndex('foo')
        self.assertHaveIndex('spam')

    def test_sparse_index(self):
        self.assertHaveIndex('sparse_index')
        self.assertIndexProperty('sparse_index', 'sparse')

        self.assertHaveIndex('sparse_index_unique')
        self.assertIndexProperty('sparse_index_unique', 'sparse')
        self.assertIndexProperty('sparse_index_unique', 'unique')

        self.assertCompoundIndex([('sparse_index_cmp_1', 1),
                                  ('sparse_index_cmp_2', 1)])
        self.assertCompoundIndex([('sparse_index_cmp_1', 1),
                                  ('sparse_index_cmp_2', 1)])

    def test_compound(self):
        self.assertCompoundIndex([('regular_index', 1), ('foo', 1)])
        self.assertCompoundIndex([('a', 1), ('b', -1)], IndexTestModel2)

    def test_foreignkey(self):
        self.assertHaveIndex('foreignkey_index_id')

    def test_descending(self):
        self.assertHaveIndex('descending_index', DESCENDING)
        self.assertHaveIndex('bar', DESCENDING)


class NewStyleIndexTests(TestCase):

    class order_doesnt_matter(list):

        def __eq__(self, other):
            return sorted(self) == sorted(other)

    def assertHaveIndex(self, key, **properties):
        info = get_collection(NewStyleIndexesTestModel).index_information()
        index_name = '_'.join('%s_%s' % pair for pair in key)
        default_properties = {'key': self.order_doesnt_matter(key), 'v': 1}
        self.assertIn(index_name, info)
        self.assertEqual(info[index_name],
                         dict(default_properties, **properties))

    def test_indexes(self):
        self.assertHaveIndex([('db_index', 1)])
        self.assertHaveIndex([('unique', 1)], unique=True)
        self.assertHaveIndex([('f2', 1), ('custom', 1)], unique=True)
        self.assertHaveIndex([('f2', 1), ('f3', 1)], unique=True)
        self.assertHaveIndex([('f1', -1)])
        self.assertHaveIndex([('f2', 1)], sparse=True)
        self.assertHaveIndex([('custom', -1), ('f3', 1)])
        self.assertHaveIndex([('geo', '2d')])
        self.assertHaveIndex([('geo', '2d'), ('f2', 1)], min=42, max=21)
        self.assertHaveIndex([('dict1.foo', 1)])
        self.assertHaveIndex([('dict_custom.foo', 1)])
        self.assertHaveIndex([('embedded.a2', 1)])
        self.assertHaveIndex([('embedded_list.a2', 1)])


class GridFSFieldTests(TestCase):

    def tearDown(self):
        get_collection(GridFSFieldTestModel).files.remove()

    def test_empty(self):
        obj = GridFSFieldTestModel.objects.create()
        self.assertEqual(obj.gridfile, None)
        self.assertEqual(obj.gridstring, '')

    def test_gridfile(self):
        fh = open(__file__)
        fh.seek(42)
        obj = GridFSFieldTestModel(gridfile=fh)
        self.assert_(obj.gridfile is fh)
        obj.save()
        self.assert_(obj.gridfile is fh)
        obj = GridFSFieldTestModel.objects.get()
        self.assertIsInstance(obj.gridfile, GridOut)
        fh.seek(42)
        self.assertEqual(obj.gridfile.read(), fh.read())

    def test_gridstring(self):
        data = open(__file__).read()
        obj = GridFSFieldTestModel(gridstring=data)
        self.assert_(obj.gridstring is data)
        obj.save()
        self.assert_(obj.gridstring is data)
        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(obj.gridstring, data)

    def test_caching(self):
        """Make sure GridFS files are read only once."""
        GridFSFieldTestModel.objects.create(gridfile=open(__file__))
        obj = GridFSFieldTestModel.objects.get()
        meta = GridFSFieldTestModel._meta.fields[1]._get_meta(obj)
        self.assertEqual(meta.filelike, None)
        obj.gridfile # Fetches the file from GridFS.
        self.assertNotEqual(meta.filelike, None)
        # From now on, the file should be looked up in the cache.
        # To verify this, we compromise the cache with a sentinel object:
        sentinel = object()
        meta.filelike = sentinel
        self.assertEqual(obj.gridfile, sentinel)

    def _test_versioning_delete(self, field, versioning, delete):
        col = get_collection(GridFSFieldTestModel).files
        get_meta = GridFSFieldTestModel._meta.get_field(field)._get_meta

        obj = GridFSFieldTestModel.objects.create()
        self.assertEqual(col.count(), 0)
        obj.delete()

        obj = GridFSFieldTestModel.objects.create(**{field: 'a'})
        self.assertEqual(col.count(), 1)

        old_oid = get_meta(obj).oid
        self.assertNotEqual(old_oid, None)
        setattr(obj, field, 'a')
        obj.save()
        self.assertEqual(get_meta(obj).oid, old_oid)
        self.assertEqual(col.count(), 1)

        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(getattr(obj, field).read(), 'a')
        setattr(obj, field, 'b')
        obj.save()
        self.assertEqual(col.count(), 2 if versioning else 1)

        old_oid = get_meta(obj).oid
        setattr(obj, field, 'b')
        obj.save()
        self.assertEqual(get_meta(obj).oid, old_oid)
        self.assertEqual(col.count(), 2 if versioning else 1)

        setattr(obj, field, 'c')
        obj.save()
        self.assertEqual(col.count(), 3 if versioning else 1)

        setattr(obj, field, 'd')
        obj.save()
        self.assertEqual(col.count(), 4 if versioning else 1)

        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(getattr(obj, field).read(), 'd')

        setattr(obj, field, 'e')
        obj.save()
        self.assertEqual(col.count(), 5 if versioning else 1)

        setattr(obj, field, 'f')
        obj.save()
        self.assertEqual(col.count(), 6 if versioning else 1)

        obj.delete()
        self.assertEqual(col.count(),
                         0 if delete else (6 if versioning else 1))

    def test_delete(self):
        self._test_versioning_delete('gridfile', versioning=False,
                                     delete=True)

    def test_nodelete(self):
        self._test_versioning_delete('gridfile_nodelete', versioning=False,
                                     delete=False)

    def test_versioning(self):
        self._test_versioning_delete('gridfile_versioned', versioning=True,
                                     delete=False)

    def test_versioning_delete(self):
        self._test_versioning_delete('gridfile_versioned_delete',
                                     versioning=True, delete=True)

    def test_multiple_save_regression(self):
        col = get_collection(GridFSFieldTestModel).files
        o = GridFSFieldTestModel.objects.create(gridfile='asd')
        self.assertEqual(col.count(), 1)
        o.save()
        self.assertEqual(col.count(), 1)
        o = GridFSFieldTestModel.objects.get()
        o.save()
        self.assertEqual(col.count(), 1)

    def test_update(self):
        self.assertRaisesRegexp(
            DatabaseError, "Updates on GridFSFields are not allowed.",
            GridFSFieldTestModel.objects.update, gridfile='x')


class CappedCollectionTests(TestCase):

    def test_collection_size(self):
        for _ in range(100):
            CappedCollection.objects.create()
        self.assertLess(CappedCollection.objects.count(), 100)

    def test_collection_max(self):
        for _ in range(100):
            CappedCollection2.objects.create()
        self.assertEqual(CappedCollection2.objects.count(), 2)

    def test_reverse_natural(self):
        for n in [1, 2, 3]:
            CappedCollection3.objects.create(n=n)

        self.assertEqualLists(
            CappedCollection3.objects.values_list('n', flat=True),
            [1, 2, 3])

        self.assertEqualLists(
            CappedCollection3.objects.reverse().values_list('n', flat=True),
            [3, 2, 1])
