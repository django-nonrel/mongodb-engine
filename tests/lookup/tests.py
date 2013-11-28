from datetime import datetime
from operator import attrgetter

from django.core.exceptions import FieldError
from django.db import connection
from django.db.utils import DatabaseError
from django.test import TestCase, skipUnlessDBFeature

# handle pymongo backward compatibility
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

from models import Author, Article, Tag


class LookupTests(TestCase):

    def setUp(self):
        # Create a few Authors.
        self.au1 = Author(name='Author 1')
        self.au1.save()
        self.au2 = Author(name='Author 2')
        self.au2.save()
        # Create a couple of Articles.
        self.a1 = Article(headline='Article 1',
                          pub_date=datetime(2005, 7, 26), author=self.au1)
        self.a1.save()
        self.a2 = Article(headline='Article 2',
                          pub_date=datetime(2005, 7, 27), author=self.au1)
        self.a2.save()
        self.a3 = Article(headline='Article 3',
                          pub_date=datetime(2005, 7, 27), author=self.au1)
        self.a3.save()
        self.a4 = Article(headline='Article 4',
                          pub_date=datetime(2005, 7, 28), author=self.au1)
        self.a4.save()
        self.a5 = Article(headline='Article 5',
                          pub_date=datetime(2005, 8, 1, 9, 0),
                          author=self.au2)
        self.a5.save()
        self.a6 = Article(headline='Article 6',
                          pub_date=datetime(2005, 8, 1, 8, 0),
                          author=self.au2)
        self.a6.save()
        self.a7 = Article(headline='Article 7',
                          pub_date=datetime(2005, 7, 27), author=self.au2)
        self.a7.save()
        # Create a few Tags.
        self.t1 = Tag(name='Tag 1')
        self.t1.save()
        self.t1.articles.add(self.a1, self.a2, self.a3)
        self.t2 = Tag(name='Tag 2')
        self.t2.save()
        self.t2.articles.add(self.a3, self.a4, self.a5)
        self.t3 = Tag(name='Tag 3')
        self.t3.save()
        self.t3.articles.add(self.a5, self.a6, self.a7)

    def test_exists(self):
        # We can use .exists() to check that there are some.
        self.assertTrue(Article.objects.exists())
        for a in Article.objects.all():
            a.delete()
        # There should be none now!
        self.assertFalse(Article.objects.exists())

    @skipUnlessDBFeature('supports_date_lookup_using_string')
    def test_lookup_date_as_str(self):
        # A date lookup can be performed using a string search.
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__startswith='2005'),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])

    def test_iterator(self):
        # Each QuerySet gets iterator(), which is a generator that
        # "lazily" returns results using database-level iteration.
        self.assertQuerysetEqual(
            Article.objects.iterator(),
            [
                'Article 5',
                'Article 6',
                'Article 4',
                'Article 2',
                'Article 3',
                'Article 7',
                'Article 1',
            ],
            transform=attrgetter('headline'))
        # iterator() can be used on any QuerySet.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__endswith='4').iterator(),
            ['Article 4'],
            transform=attrgetter('headline'))

    def test_count(self):
        # count() returns the number of objects matching search criteria.
        self.assertEqual(Article.objects.count(), 7)
        self.assertEqual(
            Article.objects.filter(pub_date__exact=datetime(2005, 7, 27))
                .count(), 3)
        self.assertEqual(
            Article.objects.filter(headline__startswith='Blah blah')
                .count(), 0)

        # count() should respect sliced query sets.
        articles = Article.objects.all()
        self.assertEqual(articles.count(), 7)
        self.assertEqual(articles[:4].count(), 4)
        self.assertEqual(articles[1:100].count(), 6)
        self.assertEqual(articles[10:100].count(), 0)

        # Date and date/time lookups can also be done with strings.
        self.assertEqual(
            Article.objects.filter(pub_date__exact='2005-07-27 00:00:00')
                .count(), 3)

    def test_in_bulk(self):
        # in_bulk() takes a list of IDs and returns a dictionary
        # mapping IDs to objects.
        arts = Article.objects.in_bulk([self.a1.id, self.a2.id])
        self.assertEqual(arts[self.a1.id], self.a1)
        self.assertEqual(arts[self.a2.id], self.a2)
        self.assertEqual(
            Article.objects.in_bulk([self.a3.id]), {self.a3.id: self.a3})
        self.assertEqual(
            Article.objects.in_bulk(set([self.a3.id])), {self.a3.id: self.a3})
        self.assertEqual(
            Article.objects.in_bulk(frozenset([self.a3.id])),
            {self.a3.id: self.a3})
        self.assertEqual(
            Article.objects.in_bulk((self.a3.id,)), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk([ObjectId()]), {})
        self.assertEqual(Article.objects.in_bulk([]), {})
        self.assertRaises(DatabaseError, Article.objects.in_bulk, 'foo')
        self.assertRaises(TypeError, Article.objects.in_bulk)
        self.assertRaises(TypeError, Article.objects.in_bulk,
                          headline__startswith='Blah')

    def test_values(self):
        # values() returns a list of dictionaries instead of object
        # instances -- and you can specify which fields you want to
        # retrieve.
        identity = lambda x: x
        self.assertQuerysetEqual(
            Article.objects.values('headline'),
            [
                {'headline': u'Article 5'},
                {'headline': u'Article 6'},
                {'headline': u'Article 4'},
                {'headline': u'Article 2'},
                {'headline': u'Article 3'},
                {'headline': u'Article 7'},
                {'headline': u'Article 1'},
            ],
            transform=identity)
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__exact=datetime(2005, 7, 27))
                .values('id'),
            [{'id': self.a2.id}, {'id': self.a3.id}, {'id': self.a7.id}],
            transform=identity)
        self.assertQuerysetEqual(
            Article.objects.values('id', 'headline'),
            [
                {'id': self.a5.id, 'headline': 'Article 5'},
                {'id': self.a6.id, 'headline': 'Article 6'},
                {'id': self.a4.id, 'headline': 'Article 4'},
                {'id': self.a2.id, 'headline': 'Article 2'},
                {'id': self.a3.id, 'headline': 'Article 3'},
                {'id': self.a7.id, 'headline': 'Article 7'},
                {'id': self.a1.id, 'headline': 'Article 1'},
            ],
            transform=identity)
        # You can use values() with iterator() for memory savings,
        # because iterator() uses database-level iteration.
        self.assertQuerysetEqual(
            Article.objects.values('id', 'headline').iterator(),
            [
                {'headline': u'Article 5', 'id': self.a5.id},
                {'headline': u'Article 6', 'id': self.a6.id},
                {'headline': u'Article 4', 'id': self.a4.id},
                {'headline': u'Article 2', 'id': self.a2.id},
                {'headline': u'Article 3', 'id': self.a3.id},
                {'headline': u'Article 7', 'id': self.a7.id},
                {'headline': u'Article 1', 'id': self.a1.id},
            ],
            transform=identity)

    def test_values_list(self):
        # values_list() is similar to values(), except that the results
        # are returned as a list of tuples, rather than a list of
        # dictionaries. Within each tuple, the order of the elements is
        # the same as the order of fields in the values_list() call.
        identity = lambda x: x
        self.assertQuerysetEqual(
            Article.objects.values_list('headline'),
            [
                (u'Article 5',),
                (u'Article 6',),
                (u'Article 4',),
                (u'Article 2',),
                (u'Article 3',),
                (u'Article 7',),
                (u'Article 1',),
            ], transform=identity)
        self.assertQuerysetEqual(
            Article.objects.values_list('id').order_by('id'),
            [(self.a1.id,), (self.a2.id,), (self.a3.id,), (self.a4.id,),
             (self.a5.id,), (self.a6.id,), (self.a7.id,)],
            transform=identity)
        self.assertQuerysetEqual(
            Article.objects.values_list('id', flat=True).order_by('id'),
            [self.a1.id, self.a2.id, self.a3.id, self.a4.id, self.a5.id,
             self.a6.id, self.a7.id],
            transform=identity)
        self.assertRaises(TypeError, Article.objects.values_list, 'id',
                          'headline', flat=True)

    def test_get_next_previous_by(self):
        # Every DateField and DateTimeField creates get_next_by_FOO()
        # and get_previous_by_FOO() methods. In the case of identical
        # date values, these methods will use the ID as a fallback
        # check. This guarantees that no records are skipped or
        # duplicated.
        self.assertEqual(repr(self.a1.get_next_by_pub_date()),
                         '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_next_by_pub_date()),
                         '<Article: Article 3>')
        self.assertEqual(
            repr(self.a2.get_next_by_pub_date(headline__endswith='6')),
            '<Article: Article 6>')
        self.assertEqual(repr(self.a3.get_next_by_pub_date()),
                         '<Article: Article 7>')
        self.assertEqual(repr(self.a4.get_next_by_pub_date()),
                         '<Article: Article 6>')
        self.assertRaises(Article.DoesNotExist, self.a5.get_next_by_pub_date)
        self.assertEqual(repr(self.a6.get_next_by_pub_date()),
                         '<Article: Article 5>')
        self.assertEqual(repr(self.a7.get_next_by_pub_date()),
                         '<Article: Article 4>')

        self.assertEqual(repr(self.a7.get_previous_by_pub_date()),
                         '<Article: Article 3>')
        self.assertEqual(repr(self.a6.get_previous_by_pub_date()),
                         '<Article: Article 4>')
        self.assertEqual(repr(self.a5.get_previous_by_pub_date()),
                         '<Article: Article 6>')
        self.assertEqual(repr(self.a4.get_previous_by_pub_date()),
                         '<Article: Article 7>')
        self.assertEqual(repr(self.a3.get_previous_by_pub_date()),
                         '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_previous_by_pub_date()),
                         '<Article: Article 1>')

    def test_escaping(self):
        # Underscores, percent signs and backslashes have special
        # meaning in the underlying SQL code, but Django handles
        # the quoting of them automatically.
        a8 = Article(headline='Article_ with underscore',
                     pub_date=datetime(2005, 11, 20))
        a8.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article'),
            [
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article_'),
            ['<Article: Article_ with underscore>'])
        a9 = Article(headline='Article% with percent sign',
                     pub_date=datetime(2005, 11, 21))
        a9.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article'),
            [
                '<Article: Article% with percent sign>',
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article%'),
            ['<Article: Article% with percent sign>'])
        a10 = Article(headline='Article with \\ backslash',
                      pub_date=datetime(2005, 11, 22))
        a10.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='\\'),
            ['<Article: Article with \ backslash>'])

    def test_exclude(self):
        a8 = Article.objects.create(headline='Article_ with underscore',
                                    pub_date=datetime(2005, 11, 20))
        a9 = Article.objects.create(headline='Article% with percent sign',
                                    pub_date=datetime(2005, 11, 21))
        a10 = Article.objects.create(headline='Article with \\ backslash',
                                     pub_date=datetime(2005, 11, 22))

        # exclude() is the opposite of filter() when doing lookups:
        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='Article')
                .exclude(headline__contains='with'),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.exclude(headline__startswith='Article_'),
            [
                '<Article: Article with \\ backslash>',
                '<Article: Article% with percent sign>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])
        self.assertQuerysetEqual(
            Article.objects.exclude(headline='Article 7'),
            [
                '<Article: Article with \\ backslash>',
                '<Article: Article% with percent sign>',
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 1>',
            ])

    def test_none(self):
        # none() returns an EmptyQuerySet that behaves like any other
        # QuerySet object.
        self.assertQuerysetEqual(Article.objects.none(), [])
        self.assertQuerysetEqual(
            Article.objects.none().filter(headline__startswith='Article'), [])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article').none(), [])
        self.assertEqual(Article.objects.none().count(), 0)
        self.assertEqual(
            Article.objects.none()
                .update(headline="This should not take effect"), 0)
        self.assertQuerysetEqual(
            [article for article in Article.objects.none().iterator()],
            [])

    def test_in(self):
        # using __in with an empty list should return an
        # empty query set.
        self.assertQuerysetEqual(Article.objects.filter(id__in=[]), [])
        self.assertQuerysetEqual(
            Article.objects.exclude(id__in=[]),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ])

    def test_error_messages(self):
        # Programming errors are pointed out with nice error messages.
        try:
            Article.objects.filter(pub_date_year='2005').count()
            self.fail("FieldError not raised.")
        except FieldError, ex:
            self.assertEqual(
                str(ex),
                "Cannot resolve keyword 'pub_date_year' into field. "
                "Choices are: author, headline, id, pub_date, tag")
        try:
            Article.objects.filter(headline__starts='Article')
            self.fail("FieldError not raised.")
        except FieldError, ex:
            self.assertEqual(
                str(ex),
                "Join on field 'headline' not permitted. "
                "Did you misspell 'starts' for the lookup type?")

    def test_regex(self):
        # Create some articles with a bit more interesting headlines
        # for testing field lookups:
        for a in Article.objects.all():
            a.delete()
        now = datetime.now()
        a1 = Article(pub_date=now, headline='f')
        a1.save()
        a2 = Article(pub_date=now, headline='fo')
        a2.save()
        a3 = Article(pub_date=now, headline='foo')
        a3.save()
        a4 = Article(pub_date=now, headline='fooo')
        a4.save()
        a5 = Article(pub_date=now, headline='hey-Foo')
        a5.save()
        a6 = Article(pub_date=now, headline='bar')
        a6.save()
        a7 = Article(pub_date=now, headline='AbBa')
        a7.save()
        a8 = Article(pub_date=now, headline='baz')
        a8.save()
        a9 = Article(pub_date=now, headline='baxZ')
        a9.save()
        # Zero-or-more.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo*'),
            ['<Article: f>', '<Article: fo>', '<Article: foo>',
             '<Article: fooo>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'fo*'),
            [
                '<Article: f>',
                '<Article: fo>',
                '<Article: foo>',
                '<Article: fooo>',
                '<Article: hey-Foo>',
            ])
        # One-or-more.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo+'),
            ['<Article: fo>', '<Article: foo>', '<Article: fooo>'])
        # Wildcard.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fooo?'),
            ['<Article: foo>', '<Article: fooo>'])
        # Leading anchor.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^b'),
            ['<Article: bar>', '<Article: baxZ>', '<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'^a'),
            ['<Article: AbBa>'])
        # Trailing anchor.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'z$'),
            ['<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'z$'),
            ['<Article: baxZ>', '<Article: baz>'])
        # Character sets.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba[rz]'),
            ['<Article: bar>', '<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba.[RxZ]'),
            ['<Article: baxZ>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'ba[RxZ]'),
            ['<Article: bar>', '<Article: baxZ>', '<Article: baz>'])

        # And more articles:
        a10 = Article(pub_date=now, headline='foobar')
        a10.save()
        a11 = Article(pub_date=now, headline='foobaz')
        a11.save()
        a12 = Article(pub_date=now, headline='ooF')
        a12.save()
        a13 = Article(pub_date=now, headline='foobarbaz')
        a13.save()
        a14 = Article(pub_date=now, headline='zoocarfaz')
        a14.save()
        a15 = Article(pub_date=now, headline='barfoobaz')
        a15.save()
        a16 = Article(pub_date=now, headline='bazbaRFOO')
        a16.save()

        # alternation
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'oo(f|b)'),
            [
                '<Article: barfoobaz>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'oo(f|b)'),
            [
                '<Article: barfoobaz>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
                '<Article: ooF>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^foo(f|b)'),
            ['<Article: foobar>', '<Article: foobarbaz>',
             '<Article: foobaz>'])

        # Greedy matching.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b.*az'),
            [
                '<Article: barfoobaz>',
                '<Article: baz>',
                '<Article: bazbaRFOO>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'b.*ar'),
            [
                '<Article: bar>',
                '<Article: barfoobaz>',
                '<Article: bazbaRFOO>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
            ])

    @skipUnlessDBFeature('supports_regex_backreferencing')
    def test_regex_backreferencing(self):
        # Grouping and backreferences.
        now = datetime.now()
        a10 = Article(pub_date=now, headline='foobar')
        a10.save()
        a11 = Article(pub_date=now, headline='foobaz')
        a11.save()
        a12 = Article(pub_date=now, headline='ooF')
        a12.save()
        a13 = Article(pub_date=now, headline='foobarbaz')
        a13.save()
        a14 = Article(pub_date=now, headline='zoocarfaz')
        a14.save()
        a15 = Article(pub_date=now, headline='barfoobaz')
        a15.save()
        a16 = Article(pub_date=now, headline='bazbaRFOO')
        a16.save()
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b(.).*b\1'),
            ['<Article: barfoobaz>', '<Article: bazbaRFOO>',
             '<Article: foobarbaz>'])
