import datetime
from operator import attrgetter

from django.db.models import F, Q
from django.db.utils import DatabaseError
# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

from models import *
from utils import *


class BasicQueryTests(TestCase):
    """Backend-agnostic query tests."""

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
        self.assertEqual(
            Blog.objects.filter(title="same title").filter(pk=blog1.pk)
                .count(), 1)
        self.assertEqual(
            Blog.objects.filter(title__startswith="same").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__istartswith="SAME").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__endswith="title").count(), 3)
        self.assertEqual(
            Blog.objects.filter(title__iendswith="Title").count(), 3)
        self.assertEqual(
            Blog.objects.filter(title__icontains="same").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__contains="same").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__iexact="same Title").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__regex="s.me.*").count(), 2)
        self.assertEqual(
            Blog.objects.filter(title__iregex="S.me.*").count(), 2)

        for record in [{'name': 'igor', 'surname': 'duck', 'age': 39},
                       {'name': 'andrea', 'surname': 'duck', 'age': 29}]:
            Person.objects.create(**record)
        self.assertEqual(
            Person.objects.filter(name="igor", surname="duck").count(), 1)
        self.assertEqual(
            Person.objects.filter(age__gte=20, surname="duck").count(), 2)

    def test_isnull(self):
        p1 = Post.objects.create(title='a')
        p2 = Post.objects.create(title='b',
                                 date_published=datetime.datetime.now())
        self.assertEqual(Post.objects.get(date_published__isnull=True), p1)
        self.assertEqual(Post.objects.get(date_published__isnull=False), p2)

    def test_range(self):
        i1 = IntegerModel.objects.create(integer=3)
        i2 = IntegerModel.objects.create(integer=10)
        self.assertEqual(IntegerModel.objects.get(integer__range=(2, 4)), i1)

    def test_change_model(self):
        blog1 = Blog.objects.create(title="blog 1")
        self.assertEqual(Blog.objects.count(), 1)
        blog1.title = "new title"
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(blog1.title, Blog.objects.all()[0].title)

    def test_skip_limit(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        Post(title="entry 1", date_published=now).save()
        Post(title="entry 2", date_published=before).save()
        Post(title="entry 3", date_published=before).save()

        self.assertEqual(len(Post.objects.order_by('-date_published')[:2]), 2)
        # With step.
        self.assertEqual(
            len(Post.objects.order_by('date_published')[1:2:1]), 1)
        self.assertEqual(len(Post.objects.order_by('date_published')[1:2]), 1)

    def test_date_datetime_and_time(self):
        self.assertEqual(DateModel().datelist, DateModel._datelist_default)
        self.assert_(DateModel().datelist is not DateModel._datelist_default)
        DateModel.objects.create()
        self.assertNotEqual(DateModel.objects.get().datetime, None)
        DateModel.objects.update(
            time=datetime.time(hour=3, minute=5, second=7),
            date=datetime.date(year=2042, month=3, day=5),
            datelist=[datetime.date(2001, 1, 2)])
        self.assertEqual(
            DateModel.objects.values_list('time', 'date', 'datelist').get(),
            (datetime.time(hour=3, minute=5, second=7),
             datetime.date(year=2042, month=3, day=5),
             [datetime.date(year=2001, month=1, day=2)]))

    def test_dates_less_and_more_than(self):
        now = datetime.datetime.now()
        before = now + datetime.timedelta(days=1)
        after = now - datetime.timedelta(days=1)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)
        entry3 = Post.objects.create(title="entry 3", date_published=after)

        self.assertEqualLists(Post.objects.filter(date_published=now),
                              [entry1])
        self.assertEqualLists(Post.objects.filter(date_published__lt=now),
                              [entry3])
        self.assertEqualLists(Post.objects.filter(date_published__gt=now),
                              [entry2])

    def test_year_date(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=365)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)

        self.assertEqualLists(
            Post.objects.filter(date_published__year=now.year), [entry1])
        self.assertEqualLists(
            Post.objects.filter(date_published__year=before.year), [entry2])

    def test_simple_foreign_keys(self):
        blog1 = Blog.objects.create(title="Blog")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)
        entry2 = Post.objects.create(title="entry 2", blog=blog1)
        self.assertEqual(Post.objects.count(), 2)
        for entry in Post.objects.all():
            self.assertEqual(
                blog1,
                entry.blog)
        blog2 = Blog.objects.create(title="Blog")
        Post.objects.create(title="entry 3", blog=blog2)
        self.assertEqualLists(
            Post.objects.filter(blog=blog1.pk).order_by('pk'),
            [entry1, entry2])
        # XXX: Uncomment this if the corresponding Django has been fixed.
        # entry_without_blog = Post.objects.create(title='x')
        # self.assertEqual(Post.objects.get(blog=None), entry_without_blog)
        # self.assertEqual(Post.objects.get(blog__isnull=True),
        #                                   entry_without_blog)

    def test_foreign_keys_bug(self):
        blog1 = Blog.objects.create(title="Blog")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)
        self.assertEqualLists(Post.objects.filter(blog=blog1), [entry1])

    def test_regex_matchers(self):
        # (startswith, contains, ... uses regex on MongoDB).
        blogs = [Blog.objects.create(title=title) for title in
                 ('Hello', 'worLd', 'D', '[(', '**', '\\')]
        for lookup, value, objs in [
            ('startswith', 'h', []),
            ('istartswith', 'h', [0]),
            ('contains', '(', [3]),
            ('icontains', 'l', [0, 1]),
            ('endswith', '\\', [5]),
            ('iendswith', 'D', [1, 2]),
        ]:
            self.assertEqualLists(
                [blog for i, blog in enumerate(blogs) if i in objs],
                Blog.objects.filter(**{'title__%s' % lookup: value})
                    .order_by('pk'))
            self.assertEqualLists(
                [blog for i, blog in enumerate(blogs) if i not in objs],
                Blog.objects.filter(
                    ~Q(**{'title__%s' % lookup: value})).order_by('pk'))

    def test_multiple_regex_matchers(self):
        posts = [
            {'title': 'Title A', 'content': 'Content A'},
            {'title': 'Title B', 'content': 'Content B'},
            {'title': 'foo bar', 'content': 'spam eggs'},
            {'title': 'asd asd', 'content': 'fghj fghj'},
        ]
        posts = [Post.objects.create(**post) for post in posts]

        # Test that we can combine multiple regex matchers:
        self.assertEqualLists(
            Post.objects.filter(title='Title A'),
            Post.objects.filter(title__startswith='T', title__istartswith='t')
                        .filter(title__endswith='A', title__iendswith='a')
                        .filter(title__contains='l', title__icontains='L'))

        # Test that multiple regex matchers can be used on more
        # than one field.
        self.assertEqualLists(
            Post.objects.all()[:3],
            Post.objects.filter(title__contains=' ', content__icontains='e'))

        # Test multiple negated regex matchers.
        self.assertEqual(
            Post.objects.filter(~Q(title__icontains='I'))
                        .get(~Q(title__endswith='d')),
            Post.objects.all()[2])
        self.assertEqual(
            Post.objects.filter(~Q(title__startswith='T'))
                        .get(~Q(content__startswith='s')),
            Post.objects.all()[3])

        # Test negated regex matchers combined with non-negated
        # regex matchers.
        self.assertEqual(
            Post.objects.filter(title__startswith='Title')
                        .get(~Q(title__startswith='Title A')),
            Post.objects.all()[1])
        self.assertEqual(
            Post.objects.filter(title__startswith='T', title__contains=' ')
                        .filter(content__startswith='C')
                        .get(~Q(content__contains='Y',
                                content__icontains='B')),
            Post.objects.all()[0])

        self.assertEqualLists(
            Post.objects.filter(title__startswith='T')
                        .exclude(title='Title A'),
            [posts[1]])
        self.assertEqual(
            Post.objects.exclude(title='asd asd')
                        .exclude(title__startswith='T').get(),
            posts[2])
        self.assertEqual(
            Post.objects.exclude(title__startswith='T')
                        .exclude(title='asd asd').get(),
            posts[2])

    def test_multiple_filter_on_same_name(self):
        Blog.objects.create(title='a')
        self.assertEqual(
            Blog.objects.filter(title='a').filter(title='a')
                        .filter(title='a').get(),
            Blog.objects.get())
        self.assertEqualLists(
            Blog.objects.filter(title='a').filter(title='b')
                        .filter(title='a'),
            [])

        # Tests chaining on primary keys.
        blog_id = Blog.objects.get().id
        self.assertEqual(
            Blog.objects.filter(pk=blog_id).filter(pk=blog_id).get(),
            Blog.objects.get())

    def test_negated_Q(self):
        blogs = [Blog.objects.create(title=title) for title in
                 ('blog', 'other blog', 'another blog')]
        self.assertEqualLists(
            Blog.objects.filter(title='blog') |
                Blog.objects.filter(~Q(title='another blog')),
            [blogs[0], blogs[1]])
        self.assertEqual(
            blogs[2],
            Blog.objects.get(~Q(title='blog') & ~Q(title='other blog')))
        self.assertEqualLists(
            Blog.objects.filter(~Q(title='another blog') | ~Q(title='blog') |
                                ~Q(title='aaaaa') | ~Q(title='fooo') |
                                Q(title__in=[b.title for b in blogs])),
            blogs)
        self.assertEqual(
            Blog.objects.filter(Q(title__in=['blog', 'other blog']),
                                ~Q(title__in=['blog'])).get(),
            blogs[1])
        self.assertEqual(
            Blog.objects.filter().exclude(~Q(title='blog')).get(),
            blogs[0])

    def test_exclude_plus_filter(self):
        objs = [IntegerModel.objects.create(integer=i) for i in (1, 2, 3, 4)]
        self.assertEqual(
            IntegerModel.objects.exclude(integer=1)
                                .exclude(integer=2)
                                .get(integer__gt=3),
            objs[3])
        self.assertEqual(
            IntegerModel.objects.exclude(integer=1)
                                .exclude(integer=2)
                                .get(integer=3),
            objs[2])

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

        self.assertEqualLists(
            Blog.objects.filter(title='1'),
            [obj1, obj2])
        self.assertEqualLists(
            Blog.objects.filter(title='1') | Blog.objects.filter(title='2'),
            [obj1, obj2, obj3])
        self.assertEqualLists(
            Blog.objects.filter(Q(title='2') | Q(title='3')),
            [obj3, obj4])

        self.assertEqualLists(
            Blog.objects.filter(Q(Q(title__lt='4') & Q(title__gt='2')) |
                                  Q(title='1')).order_by('id'),
            [obj1, obj2, obj4])

    def test_can_save_empty_model(self):
        obj = Empty.objects.create()
        self.assertNotEqual(obj.id, None)
        self.assertNotEqual(obj.id, 'None')
        self.assertEqual(obj, Empty.objects.get(id=obj.id))

    def test_values_query(self):
        blog = Blog.objects.create(title='fooblog')
        entry = Post.objects.create(blog=blog, title='footitle',
                                    content='foocontent')
        entry2 = Post.objects.create(blog=blog, title='footitle2',
                                     content='foocontent2')
        self.assertEqualLists(
            Post.objects.values(),
            [{'blog_id': blog.id, 'title': u'footitle', 'id': entry.id,
              'content': u'foocontent', 'date_published': None},
             {'blog_id': blog.id, 'title': u'footitle2', 'id': entry2.id,
              'content': u'foocontent2', 'date_published': None}])
        self.assertEqualLists(
            Post.objects.values('blog'),
            [{'blog': blog.id}, {'blog': blog.id}])
        self.assertEqualLists(
            Post.objects.values_list('blog_id', 'date_published'),
            [(blog.id, None), (blog.id, None)])
        self.assertEqualLists(
            Post.objects.values('title', 'content'),
            [{'title': u'footitle', 'content': u'foocontent'},
             {'title': u'footitle2', 'content': u'foocontent2'}])


class UpdateTests(TestCase):

    def test_update(self):
        blog1 = Blog.objects.create(title="Blog")
        blog2 = Blog.objects.create(title="Blog 2")
        entry1 = Post.objects.create(title="entry 1", blog=blog1)

        Post.objects.filter(pk=entry1.pk).update(blog=blog2)
        self.assertEqualLists(Post.objects.filter(blog=blog2), [entry1])

        Post.objects.filter(blog=blog2).update(title="Title has been updated")
        self.assertEqualLists(Post.objects.filter()[0].title,
                              "Title has been updated")

        Post.objects.filter(blog=blog2).update(title="Last Update Test",
                                               blog=blog1)
        self.assertEqualLists(Post.objects.filter()[0].title,
                              "Last Update Test")

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
        Person.objects.update(age=F('age') + 7)
        self.assertEqual(Person.objects.get(pk=john.id).age, 49)
        self.assertEqual(Person.objects.get(id=andy.pk).age, 2)
        Person.objects.filter(name='john').update(age=F('age')-10)
        self.assertEqual(Person.objects.get(name='john').age, 39)

    def test_update_with_F_and_db_column(self):
        # This test is simmilar to test_update_with_F but tests
        # the update with a column that has a db_column set.
        john = Person.objects.create(name='john', surname='nhoj',
                                     another_age=42)
        andy = Person.objects.create(name='andy', surname='ydna',
                                     another_age=-5)
        Person.objects.update(another_age=F('another_age') + 7)
        self.assertEqual(Person.objects.get(pk=john.id).another_age, 49)
        self.assertEqual(Person.objects.get(id=andy.pk).another_age, 2)
        Person.objects.filter(name='john').update(
            another_age=F('another_age') - 10)
        self.assertEqual(Person.objects.get(name='john').another_age, 39)

    def test_invalid_update_with_F(self):
        self.assertRaises(AssertionError, Person.objects.update,
                          age=F('name') + 1)


class OrderingTests(TestCase):

    def test_dates_ordering(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        entry1 = Post.objects.create(title="entry 1", date_published=now)
        entry2 = Post.objects.create(title="entry 2", date_published=before)

        self.assertEqualLists(Post.objects.order_by('-date_published'),
                              [entry1, entry2])
        self.assertEqualLists(Post.objects.order_by('date_published'),
                              [entry2, entry1])


class OrLookupsTests(TestCase):
    """Stolen from the Django test suite, shaked down for m2m tests."""

    def setUp(self):
        self.a1 = Article.objects.create(
            headline='Hello', pub_date=datetime.datetime(2005, 11, 27)).pk
        self.a2 = Article.objects.create(
            headline='Goodbye', pub_date=datetime.datetime(2005, 11, 28)).pk
        self.a3 = Article.objects.create(
            headline='Hello and goodbye',
            pub_date=datetime.datetime(2005, 11, 29)).pk

    def test_filter_or(self):
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Hello') |
                Article.objects.filter(headline__startswith='Goodbye'),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='Hello') |
                Article.objects.filter(headline__contains='bye'),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(headline__iexact='Hello') |
                Article.objects.filter(headline__contains='ood'),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello') |
                                   Q(headline__startswith='Goodbye')),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_stages(self):
        # You can shorten this syntax with code like the following,
        # which is especially useful if building the query in stages:
        articles = Article.objects.all()
        self.assertQuerysetEqual(
            articles.filter(headline__startswith='Hello') &
                articles.filter(headline__startswith='Goodbye'),
            [])
        self.assertQuerysetEqual(
            articles.filter(headline__startswith='Hello') &
                articles.filter(headline__contains='bye'),
            ['Hello and goodbye'],
            attrgetter('headline'))

    def test_pk_q(self):
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | Q(pk=self.a2)),
            ['Hello', 'Goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | Q(pk=self.a2) |
                                   Q(pk=self.a3)),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_pk_in(self):
        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[self.a1, self.a2, self.a3]),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=(self.a1, self.a2, self.a3)),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[self.a1, self.a2, self.a3]),
            ['Hello', 'Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_q_negated(self):
        # Q objects can be negated.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) | ~Q(pk=self.a2)),
            ['Hello', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.filter(~Q(pk=self.a1) & ~Q(pk=self.a2)),
            ['Hello and goodbye'],
            attrgetter('headline'), ordered=False)

        # This allows for more complex queries than filter() and
        # exclude() alone would allow.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk=self.a1) & (~Q(pk=self.a2) |
                                   Q(pk=self.a3))),
            ['Hello'],
            attrgetter('headline'), ordered=False)

    def test_complex_filter(self):
        # The 'complex_filter' method supports framework features such
        # as 'limit_choices_to' which normally take a single dictionary
        # of lookup arguments but need to support arbitrary queries via
        # Q objects too.
        self.assertQuerysetEqual(
            Article.objects.complex_filter({'pk': self.a1}),
            ['Hello'],
            attrgetter('headline'), ordered=False)

        self.assertQuerysetEqual(
            Article.objects.complex_filter(Q(pk=self.a1) | Q(pk=self.a2)),
            ['Hello', 'Goodbye'],
            attrgetter('headline'), ordered=False)

    def test_empty_in(self):
        # Passing "in" an empty list returns no results ...
        self.assertQuerysetEqual(
            Article.objects.filter(pk__in=[]),
            [], ordered=False)
        # ... but can return results if we OR it with another query.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(pk__in=[]) |
                                   Q(headline__icontains='goodbye')),
            ['Goodbye', 'Hello and goodbye'],
            attrgetter('headline'), ordered=False)

    def test_q_and(self):
        # Q arg objects are ANDed.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello'),
                                   Q(headline__contains='bye')),
            ['Hello and goodbye'],
            attrgetter('headline'))
        # Q arg AND order is irrelevant.
        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__contains='bye'),
                                     headline__startswith='Hello'),
            ['Hello and goodbye'],
            attrgetter('headline'))

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello') &
                                   Q(headline__startswith='Goodbye')),
            [])

    def test_q_exclude(self):
        self.assertQuerysetEqual(
            Article.objects.exclude(Q(headline__startswith='Hello')),
            ['Goodbye'],
            attrgetter('headline'))

    def test_other_arg_queries(self):
        # Try some arg queries with operations other than filter.
        self.assertEqual(
            Article.objects.get(Q(headline__startswith='Hello'),
                                Q(headline__contains='bye')).headline,
            'Hello and goodbye')

        self.assertEqual(
            Article.objects.filter(Q(headline__startswith='Hello') |
                                   Q(headline__contains='bye')).count(),
            3)

        self.assertQuerysetEqual(
            Article.objects.filter(Q(headline__startswith='Hello'),
                                   Q(headline__contains='bye')).values(),
            [{'headline': "Hello and goodbye", 'id': self.a3,
              'pub_date': datetime.datetime(2005, 11, 29)}],
            lambda o: o)

        self.assertEqual(
            Article.objects.filter(Q(headline__startswith='Hello'))
                           .in_bulk([self.a1, self.a2]),
            {self.a1: Article.objects.get(pk=self.a1)})
