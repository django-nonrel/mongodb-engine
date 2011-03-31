"""
    Query and regression tests,
    plus tests for django-mongodb-engine specific features
"""
import datetime

from django.db import connections
from django.db.models import F, Q
from django.db.utils import DatabaseError
from django.contrib.sites.models import Site

from gridfs import GridOut
from pymongo.objectid import ObjectId, InvalidId
from pymongo import ASCENDING, DESCENDING

from django_mongodb_engine.base import DatabaseWrapper
from django_mongodb_engine.serializer import LazyModelInstance

from .utils import *
from models import *

class QueryTests(TestCase):
    """ Backend-agnostic query tests """

    def assertQuerysetEqual(self, a, b):
        self.assertEqual(list(a), list(b))

    def test_add_and_delete_blog(self):
        Blog.objects.create(title='blog1')
        self.assertEqual(Blog.objects.count(), 1)
        blog2 = Blog.objects.create(title='blog2')
        self.assertIsInstance(blog2.pk, unicode)
        self.assertEqual(Blog.objects.count(), 2)
        blog2.delete()
        self.assertEqual(Blog.objects.count(), 1)
        Blog.objects.filter(title='blog1').delete()
        self.assertEqual(Blog.objects.count(), 0)

    def test_simple_filter(self):
        blog1 = Blog.objects.create(title="same title")
        Blog.objects.create(title="same title")
        Blog.objects.create(title="another title")
        self.assertEqual(Blog.objects.count(), 3)
        self.assertEqual(Blog.objects.get(pk=blog1.pk), blog1)
        self.assertEqual(Blog.objects.filter(title="same title").count(), 2)
        self.assertEqual(Blog.objects.filter(title="same title").filter(pk=blog1.pk).count(), 1)
        self.assertEqual(Blog.objects.filter(title__startswith="same").count(), 2)
        self.assertEqual(Blog.objects.filter(title__istartswith="SAME").count(), 2)
        self.assertEqual(Blog.objects.filter(title__endswith="title").count(), 3)
        self.assertEqual(Blog.objects.filter(title__iendswith="Title").count(), 3)
        self.assertEqual(Blog.objects.filter(title__icontains="same").count(), 2)
        self.assertEqual(Blog.objects.filter(title__contains="same").count(), 2)
        self.assertEqual(Blog.objects.filter(title__iexact="same Title").count(), 2)
        self.assertEqual(Blog.objects.filter(title__regex="s.me.*").count(), 2)
        self.assertEqual(Blog.objects.filter(title__iregex="S.me.*").count(), 2)

        for record in [{'name' : 'igor', 'surname' : 'duck', 'age' : 39},
                       {'name' : 'andrea', 'surname' : 'duck', 'age' : 29}]:
            Person.objects.create(**record)
        self.assertEqual(Person.objects.filter(name="igor", surname="duck").count(), 1)
        self.assertEqual(Person.objects.filter(age__gte=20, surname="duck").count(), 2)

    def test_change_model(self):
        blog1 = Blog.objects.create(title="blog 1")
        self.assertEqual(Blog.objects.count(), 1)
        blog1.title = "new title"
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(blog1.title, Blog.objects.all()[0].title)

    def test_dates_ordering(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)

        self.assertQuerysetEqual(Post.objects.order_by('-date_published'),
                                 [entry1, entry2])
        self.assertQuerysetEqual(Post.objects.order_by('date_published'),
                                 [entry2, entry1])

    def test_skip_limit(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        Post(title="entry 1", date_published=now).save()
        Post(title="entry 2", date_published=before).save()
        Post(title="entry 3", date_published=before).save()

        self.assertEqual(len(Post.objects.order_by('-date_published')[:2]), 2)
        # With step
        self.assertEqual(len(Post.objects.order_by('date_published')[1:2:1]), 1)
        self.assertEqual(len(Post.objects.order_by('date_published')[1:2]), 1)

    def test_values_query(self):
        blog = Blog.objects.create(title='fooblog')
        entry = Post.objects.create(blog=blog, title='footitle', content='foocontent')
        entry2 = Post.objects.create(blog=blog, title='footitle2', content='foocontent2')
        self.assertQuerysetEqual(
            Post.objects.values(),
            [{'blog_id' : blog.id, 'title' : u'footitle', 'id' : entry.id,
              'content' : u'foocontent', 'date_published' : None},
             {'blog_id' : blog.id, 'title' : u'footitle2', 'id' : entry2.id,
              'content' : u'foocontent2', 'date_published' : None}
            ]
        )
        self.assertQuerysetEqual(
            Post.objects.values('blog'),
            [{'blog' : blog.id}, {'blog' : blog.id}]
        )
        self.assertQuerysetEqual(
            Post.objects.values_list('blog_id', 'date_published'),
            [(blog.id, None), (blog.id, None)]
        )
        self.assertQuerysetEqual(
            Post.objects.values('title', 'content'),
            [{'title' : u'footitle', 'content' : u'foocontent'},
             {'title' : u'footitle2', 'content' : u'foocontent2'}]
        )

    def test_dates_less_and_more_than(self):
        now = datetime.datetime.now()
        before = now + datetime.timedelta(days=1)
        after = now - datetime.timedelta(days=1)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)
        entry3 = Post.objects.create(title="entry 3", date_published=after)

        self.assertQuerysetEqual(Post.objects.filter(date_published=now), [entry1])
        self.assertQuerysetEqual(Post.objects.filter(date_published__lt=now), [entry3])
        self.assertQuerysetEqual(Post.objects.filter(date_published__gt=now), [entry2])

    def test_A_query(self):
        from django_mongodb_engine.query import A
        obj1 = RawFieldModel.objects.create(raw=[{'a' : 1, 'b' : 2}])
        obj2 = RawFieldModel.objects.create(raw=[{'a' : 1, 'b' : 3}])
        self.assertQuerysetEqual(RawFieldModel.objects.filter(raw=A('a', 1)),
                                 [obj1, obj2])
        self.assertEqual(RawFieldModel.objects.get(raw=A('b', 2)), obj1)
        self.assertEqual(RawFieldModel.objects.get(raw=A('b', 3)), obj2)

    def test_simple_foreign_keys(self):
        blog1 = Blog.objects.create(title="Blog")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)
        entry2 = Post.objects.create(title="entry 2", blog=blog1)
        self.assertEqual(Post.objects.count(), 2)
        for entry in Post.objects.all():
            self.assertEqual(
                blog1,
                entry.blog
            )
        blog2 = Blog.objects.create(title="Blog")
        Post.objects.create(title="entry 3", blog=blog2)
        self.assertQuerysetEqual(Post.objects.filter(blog=blog1.pk),
                                 [entry1, entry2])
        # XXX Uncomment this if the corresponding Django has been fixed
        #entry_without_blog = Post.objects.create(title='x')
        #self.assertEqual(Post.objects.get(blog=None), entry_without_blog)
        #self.assertEqual(Post.objects.get(blog__isnull=True), entry_without_blog)

    def test_foreign_keys_bug(self):
        blog1 = Blog.objects.create(title="Blog")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)
        self.assertQuerysetEqual(Post.objects.filter(blog=blog1), [entry1])

    def test_update(self):
        blog1 = Blog.objects.create(title="Blog")
        blog2 = Blog.objects.create(title="Blog 2")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)

        Post.objects.filter(pk=entry1.pk).update(blog=blog2)
        self.assertQuerysetEqual(Post.objects.filter(blog=blog2), [entry1])

        Post.objects.filter(blog=blog2).update(title="Title has been updated")
        self.assertQuerysetEqual(Post.objects.filter()[0].title, "Title has been updated")

        Post.objects.filter(blog=blog2).update(title="Last Update Test", blog=blog1)
        self.assertQuerysetEqual(Post.objects.filter()[0].title, "Last Update Test")

        self.assertEqual(Post.objects.filter(blog=blog1).count(), 1)
        self.assertEqual(Blog.objects.filter(title='Blog').count(), 1)
        Blog.objects.update(title='Blog')
        self.assertEqual(Blog.objects.filter(title='Blog').count(), 2)

    def test_update_id(self):
        self.assertRaisesRegexp(DatabaseError, "Can not modify _id",
                                Post.objects.update, id=ObjectId())

    def test_update_with_F(self):
        john = Person.objects.create(name='john', surname='nhoj', age=42)
        andy = Person.objects.create(name='andy', surname='ydna', age=-5)
        Person.objects.update(age=F('age')+7)
        self.assertEqual(Person.objects.get(pk=john.id).age, 49)
        self.assertEqual(Person.objects.get(id=andy.pk).age, 2)
        Person.objects.filter(name='john').update(age=F('age')-10)
        self.assertEqual(Person.objects.get(name='john').age, 39)

    def test_regex_matchers(self):
        objs = [Blog.objects.create(title=title) for title in
                ('Hello', 'worLd', '[(', '**', '\\')]
        self.assertEqual(list(Blog.objects.filter(title__startswith='h')), [])
        self.assertEqual(list(Blog.objects.filter(title__istartswith='h')), [objs[0]])
        self.assertEqual(list(Blog.objects.filter(title__contains='(')), [objs[2]])
        self.assertEqual(list(Blog.objects.filter(title__endswith='\\')), [objs[4]])

    def test_multiple_regex_matchers(self):
        objs = [Person.objects.create(name=a, surname=b) for a, b in
                (name.split() for name in ['donald duck', 'dagobert duck', 'daisy duck'])]

        filters = dict(surname__startswith='duck', surname__istartswith='duck',
                       surname__endswith='duck', surname__iendswith='duck',
                       surname__contains='duck', surname__icontains='duck')
        base_query = Person.objects \
                        .filter(**filters) \
                        .filter(~Q(surname__contains='just-some-random-condition',
                                   surname__endswith='hello world'))
        #base_query = base_query | base_query

        self.assertEqual(base_query.filter(name__iendswith='d')[0], objs[0])
        self.assertEqual(base_query.filter(name='daisy').get(), objs[2])

    def test_multiple_filter_on_same_name(self):
        Blog.objects.create(title='a')
        self.assertEqual(
            Blog.objects.filter(title='a').filter(title='a').filter(title='a').get(),
            Blog.objects.get()
        )
        self.assertQuerysetEqual(
            Blog.objects.filter(title='a').filter(title='b').filter(title='a'),
            []
        )

    def test_negated_Q(self):
        blogs = [Blog.objects.create(title=title) for title in
                 ('blog', 'other blog', 'another blog')]
        self.assertQuerysetEqual(
            Blog.objects.filter(title='blog') | Blog.objects.filter(~Q(title='another blog')),
            [blogs[0], blogs[1]]
        )
        self.assertRaises(
            DatabaseError,
            lambda: Blog.objects.filter(~Q(title='blog') & ~Q(title='other blog')).get()
        )
        self.assertQuerysetEqual(
            Blog.objects.filter(~Q(title='another blog')
                                | ~Q(title='blog')
                                | ~Q(title='aaaaa')
                                | ~Q(title='fooo')
                                | Q(title__in=[b.title for b in blogs])),
            blogs
        )
        self.assertEqual(
            Blog.objects.filter(Q(title__in=['blog', 'other blog']),
                                ~Q(title__in=['blog'])).get(),
            blogs[1]
        )
        self.assertEqual(
            Blog.objects.filter().exclude(~Q(title='blog')).get(),
            blogs[0]
        )

    def test_nin(self):
        Blog.objects.create(title='a')
        Blog.objects.create(title='b')
        self.assertEqual(Blog.objects.get(~Q(title__in='b')),
                         Blog.objects.get(title='a'))

    def test_simple_or_queries(self):
        obj1 = Blog.objects.create(title='1')
        obj2 = Blog.objects.create(title='1')
        obj3 = Blog.objects.create(title='2')
        obj4 = Blog.objects.create(title='3')

        self.assertQuerysetEqual(
            Blog.objects.filter(title='1'),
            [obj1, obj2]
        )
        self.assertQuerysetEqual(
            Blog.objects.filter(title='1') | Blog.objects.filter(title='2'),
            [obj1, obj2, obj3]
        )
        self.assertQuerysetEqual(
            Blog.objects.filter(Q(title='2') | Q(title='3')),
            [obj3, obj4]
        )

        self.assertQuerysetEqual(
            Blog.objects.filter(Q(Q(title__lt='4') & Q(title__gt='2'))
                                  | Q(title='1')).order_by('id'),
            [obj1, obj2, obj4]
        )

    def test_date_datetime_and_time(self):
        self.assertEqual(DateModel().datelist, DateModel._datelist_default)
        self.assert_(DateModel().datelist is not DateModel._datelist_default)
        DateModel.objects.create()
        self.assertNotEqual(DateModel.objects.get().datetime, None)
        DateModel.objects.update(
            time=datetime.time(hour=3, minute=5, second=7),
            date=datetime.date(year=2042, month=3, day=5),
            datelist=[datetime.date(2001, 1, 2)]
        )
        self.assertEqual(
            DateModel.objects.values_list('time', 'date', 'datelist').get(),
            (datetime.time(hour=3, minute=5, second=7),
             datetime.date(year=2042, month=3, day=5),
             [datetime.date(year=2001, month=1, day=2)])
        )


class MongoDBEngineTests(TestCase):
    """ Tests for mongodb-engine specific features """

    def test_mongometa(self):
        self.assertEqual(Post._meta.descending_indexes, ['title'])

    def test_lazy_model_instance(self):
        l1 = LazyModelInstance(Post, 'some-pk')
        l2 = LazyModelInstance(Post, 'some-pk')

        self.assertEqual(l1, l2)

        obj = Post(title='foobar')
        obj.save()

        l3 = LazyModelInstance(Post, obj.id)
        self.assertEqual(l3._wrapped, None)
        self.assertEqual(obj, l3)
        self.assertNotEqual(l3._wrapped, None)

    def test_lazy_model_instance_in_list(self):
        from django.conf import settings
        from bson.errors import InvalidDocument

        obj = RawFieldModel(raw=[])
        related = Blog(title='foo')
        obj.raw.append(related)
        self.assertRaises(InvalidDocument, obj.save)

        settings.MONGODB_AUTOMATIC_REFERENCING = True
        connections._connections.values()[0]._add_serializer()
        obj.save()
        self.assertNotEqual(related.id, None)
        obj = RawFieldModel.objects.get()
        self.assertEqual(obj.raw[0]._wrapped, None)
        # query will be done NOW:
        self.assertEqual(obj.raw[0].title, 'foo')
        self.assertNotEqual(obj.raw[0]._wrapped, None)

    def test_nice_yearmonthday_query_exception(self):
        for x in ('year', 'month', 'day'):
            key = 'date_published__%s' % x
            self.assertRaisesRegexp(DatabaseError, "MongoDB does not support year/month/day queries",
                                    lambda: Post.objects.get(**{key : 1}))

    def test_nice_int_objectid_exception(self):
        msg = "AutoField \(default primary key\) values must be strings " \
              "representing an ObjectId on MongoDB \(got %r instead\)"
        self.assertRaisesRegexp(InvalidId, msg % u'helloworld...',
                                Blog.objects.create, id='helloworldwhatsup')
        self.assertRaisesRegexp(
            InvalidId, (msg % u'5') + ". Please make sure your SITE_ID contains a valid ObjectId.",
            Site.objects.get, id='5'
        )

    def test_generic_field(self):
        for obj in [['foo'], {'bar' : 'buzz'}]:
            id = RawFieldModel.objects.create(raw=obj).id
            self.assertEqual(RawFieldModel.objects.get(id=id).raw, obj)

    def test_databasewrapper_api(self):
        from pymongo.connection import Connection
        from pymongo.database import Database
        from pymongo.collection import Collection
        from random import shuffle

        if settings.DEBUG:
            from django_mongodb_engine.utils import CollectionDebugWrapper as Collection

        for wrapper in (
            connections['default'],
            DatabaseWrapper(connections['default'].settings_dict.copy())
        ):
            calls = [
                lambda: self.assertIsInstance(wrapper.get_collection('foo'), Collection),
                lambda: self.assertIsInstance(wrapper.database, Database),
                lambda: self.assertIsInstance(wrapper.connection, Connection)
            ]
            shuffle(calls)
            for call in calls:
                call()

class DatabaseOptionTests(TestCase):
    """ Tests for MongoDB-specific database options """

    class custom_database_wrapper(object):
        def __init__(self, settings, **kwargs):
            self.new_wrapper = DatabaseWrapper(
                dict(connections['default'].settings_dict, **settings),
                **kwargs
            )

        def __enter__(self):
            self._old_connection = connections._connections['default']
            connections._connections['default'] = self.new_wrapper
            self.new_wrapper._connect()
            return self.new_wrapper

        def __exit__(self, *exc_info):
            self.new_wrapper.connection.disconnect()
            connections._connections['default'] = self._old_connection

    def test_pymongo_connection_args(self):
        class foodict(dict):
            pass

        with self.custom_database_wrapper({
            'OPTIONS' : {
                'SLAVE_OKAY' : True,
                'NETWORK_TIMEOUT' : 42,
                'TZ_AWARE' : True,
                'DOCUMENT_CLASS' : foodict
            }
        }) as connection:
            for name, value in connection.settings_dict['OPTIONS'].iteritems():
                name = '_Connection__%s' % name.lower()
                self.assertEqual(connection.connection.__dict__[name], value)

    def test_operation_flags(self):
        from textwrap import dedent
        from pymongo.collection import Collection as PyMongoCollection

        def test_setup(flags, **method_kwargs):
            class Collection(PyMongoCollection):
                _method_kwargs = {}
                for name in method_kwargs:
                    exec dedent('''
                    def {0}(self, *a, **k):
                        assert '{0}' not in self._method_kwargs
                        self._method_kwargs['{0}'] = k
                        super(self.__class__, self).{0}(*a, **k)'''.format(name))

            options = {'OPTIONS' : {'OPERATIONS' : flags}}
            with self.custom_database_wrapper(options, collection_class=Collection):
                Blog.objects.create(title='foo')
                Blog.objects.update(title='foo')
                Blog.objects.all().delete()

            for name in method_kwargs:
                self.assertEqual(method_kwargs[name],
                                 Collection._method_kwargs[name])

        test_setup({}, save={}, update={'multi' : True}, remove={})
        test_setup(
            {'safe' : True, 'w' : True},
            save={'safe' : True, 'w' : True},
            update={'safe' : True, 'w' : True, 'multi' : True},
            remove={'safe' : True, 'w' : True}
        )
        test_setup(
            {'delete' : {'safe' : True}, 'update' : {}},
            save={},
            update={'multi' : True},
            remove={'safe' : True}
        )
        test_setup(
            {'insert' : {'fsync' : True}, 'delete' : {'w' : True, 'fsync' : True}},
            save={},
            update={'multi' : True},
            remove={'w' : True, 'fsync' : True}
        )

    def test_legacy_flags(self):
        options = {'SAFE_INSERTS' : True, 'WAIT_FOR_SLAVES' : 5}
        with self.custom_database_wrapper(options) as wrapper:
            self.assertTrue(wrapper.operation_flags['save']['safe'])
            self.assertEqual(wrapper.operation_flags['save']['w'], 5)

class IndexTests(TestCase):
    def setUp(self):
        from django.core.management import call_command
        from cStringIO import StringIO
        import sys
        _stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            call_command('sqlindexes', 'general')
        finally:
            sys.stdout = _stdout

    def assertHaveIndex(self, field_name, direction=ASCENDING):
        info = get_collection(IndexTestModel).index_information()
        index_name = field_name + ['_1', '_-1'][direction==DESCENDING]
        self.assertIn(index_name, info)
        self.assertIn((field_name, direction), info[index_name]['key'])

    # Assumes fields as [(name, direction), (name, direction)]
    def assertCompoundIndex(self, fields, model=IndexTestModel):
        info = get_collection(model).index_information()
        index_names = [field[0] + ['_1', '_-1'][field[1]==DESCENDING] for field in fields]
        index_name = "_".join(index_names)
        self.assertIn(index_name, info)
        self.assertEqual(fields, info[index_name]['key'])

    def assertIndexProperty(self, field_name, name, direction=ASCENDING):
        info = get_collection(IndexTestModel).index_information()
        index_name = field_name + ['_1', '_-1'][direction==DESCENDING]
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

        self.assertCompoundIndex([('sparse_index_cmp_1', 1), ('sparse_index_cmp_2', 1)])
        self.assertCompoundIndex([('sparse_index_cmp_1', 1), ('sparse_index_cmp_2', 1)])

    def test_compound(self):
        self.assertCompoundIndex([('regular_index', 1), ('custom_column', 1)])
        self.assertCompoundIndex([('a', 1), ('b', -1)], IndexTestModel2)

    def test_foreignkey(self):
        self.assertHaveIndex('foreignkey_index_id')

    def test_descending(self):
        self.assertHaveIndex('descending_index', DESCENDING)
        self.assertHaveIndex('bar', DESCENDING)

class GridFSFieldTests(TestCase):
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

    def test_deletion(self):
        from gridfs import NoFile
        for field in GridFSFieldTestModel._meta.fields[-2:]:
            GridFSFieldTestModel.objects.create(
                gridstring='foobar', gridfile_nodelete='spam')
            obj = GridFSFieldTestModel.objects.get()
            file_id = field._get_meta(obj).oid
            gridfs = field._get_gridfs(obj)
            obj.delete()
            if field._autodelete:
                self.assertRaises(NoFile, gridfs.get, file_id)
            else:
                self.assertIsInstance(gridfs.get(file_id), GridOut)

    def test_gridstring(self):
        data = open(__file__).read()
        obj = GridFSFieldTestModel(gridstring=data)
        self.assert_(obj.gridstring is data)
        obj.save()
        self.assert_(obj.gridstring is data)
        obj = GridFSFieldTestModel.objects.get()
        self.assertEqual(obj.gridstring, data)

    def test_caching(self):
        """ Make sure GridFS files are read only once """
        GridFSFieldTestModel.objects.create(gridfile=open(__file__))
        obj = GridFSFieldTestModel.objects.get()
        meta = GridFSFieldTestModel._meta.fields[1]._get_meta(obj)
        self.assertEqual(meta.filelike, None)
        obj.gridfile # fetches the file from GridFS
        self.assertNotEqual(meta.filelike, None)
        # from now on, the file should be looked up in the cache.
        # to verify this, we compromise the cache with a sentinel object:
        sentinel = object()
        meta.filelike = sentinel
        self.assertEqual(obj.gridfile, sentinel)

    def test_versioning(self):
        from gridfs import NoFile
        for field in GridFSFieldTestModel._meta.fields[1:3]:
            GridFSFieldTestModel.objects.create(
                gridfile='asd', gridfile_versioned='fgh')
            obj = GridFSFieldTestModel.objects.get()
            first_oid = field._get_meta(obj).oid

            #GridFSFieldTestModel.objects.update(
            #    gridfile='qwe', gridfile_versioned='rty')
            obj.gridfile = 'qwe'
            obj.gridfile_versioned = 'rty'
            obj.save()

            obj = GridFSFieldTestModel.objects.get()
            second_oid = field._get_meta(obj).oid
            assert first_oid != second_oid

            gridfs = field._get_gridfs(obj)
            self.assertIsInstance(gridfs.get(second_oid), GridOut)
            if field._versioning:
                self.assertIsInstance(gridfs.get(first_oid), GridOut)
            else:
                self.assertRaises(NoFile, gridfs.get, first_oid)

            GridFSFieldTestModel.objects.all().delete()

    def test_update(self):
        self.assertRaisesRegexp(
            DatabaseError, "Updates on GridFSFields are not allowed",
            GridFSFieldTestModel.objects.update, gridfile='x'
        )
