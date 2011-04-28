"""
    Query and regression tests,
    plus tests for django-mongodb-engine specific features
"""
import datetime

from django.db.models import F, Q
from django.db.utils import DatabaseError

from pymongo.objectid import ObjectId

from .models import *
from .utils import *

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
        obj1 = RawModel.objects.create(raw=[{'a' : 1, 'b' : 2}])
        obj2 = RawModel.objects.create(raw=[{'a' : 1, 'b' : 3}])
        self.assertQuerysetEqual(RawModel.objects.filter(raw=A('a', 1)),
                                 [obj1, obj2])
        self.assertEqual(RawModel.objects.get(raw=A('b', 2)), obj1)
        self.assertEqual(RawModel.objects.get(raw=A('b', 3)), obj2)

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

    def test_invalid_update_with_F(self):
        self.assertRaises(DatabaseError, Person.objects.update, age=F('name')+1)

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

    def test_can_save_empty_model(self):
        obj = Empty.objects.create()
        self.assertNotEqual(obj.id, None)
        self.assertNotEqual(obj.id, 'None')
        self.assertEqual(obj, Empty.objects.get(id=obj.id))
