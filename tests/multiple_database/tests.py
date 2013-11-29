import datetime
import pickle
import sys
from StringIO import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.db import connections, router, DEFAULT_DB_ALIAS
from django.db.models import signals
from django.db.utils import ConnectionRouter, DatabaseError

from models import Book, Person, Pet, Review, UserProfile

try:
    # we only have these models if the user is using multi-db, it's safe the
    # run the tests without them though.
    from models import Article, article_using
except ImportError:
    pass

from .utils import TestCase

class QueryTestCase(TestCase):
    multi_db = True

    def test_db_selection(self):
        "Check that querysets will use the default database by default"
        self.assertEqual(Book.objects.db, DEFAULT_DB_ALIAS)
        self.assertEqual(Book.objects.all().db, DEFAULT_DB_ALIAS)

        self.assertEqual(Book.objects.using('other').db, 'other')

        self.assertEqual(Book.objects.db_manager('other').db, 'other')
        self.assertEqual(Book.objects.db_manager('other').all().db, 'other')

    def test_default_creation(self):
        "Objects created on the default database don't leak onto other databases"
        # Create a book on the default database using create()
        Book.objects.create(title="Pro Django",
                            published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save()

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Dive into Python"
        )


    def test_other_creation(self):
        "Objects created on another database don't leak onto the default database"
        # Create a book on the second database
        Book.objects.using('other').create(title="Pro Django",
                                           published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
        )

        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

    def test_basic_queries(self):
        "Queries are constrained to a single database"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        dive =  Book.objects.using('other').get(published=datetime.date(2009, 5, 4))
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published=datetime.date(2009, 5, 4))

        dive = Book.objects.using('other').get(title__icontains="dive")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__icontains="dive")

        dive = Book.objects.using('other').get(title__iexact="dive INTO python")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__iexact="dive INTO python")

    def test_foreign_key_separation(self):
        "FK fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")
        george = Person.objects.create(name="George Vilches")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        chris = Person.objects.using('other').create(name="Chris Mills")

        # Save the author's favourite books
        pro.editor = george
        pro.save()

        dive.editor = chris
        dive.save()

        pro = Book.objects.using('default').get(title="Pro Django")
        self.assertEqual(pro.editor.name, "George Vilches")

        dive = Book.objects.using('other').get(title="Dive into Python")
        self.assertEqual(dive.editor.name, "Chris Mills")

        # Reget the objects to clear caches
        chris = Person.objects.using('other').get(name="Chris Mills")
        dive = Book.objects.using('other').get(title="Dive into Python")

        # Retrieve related object by descriptor. Related objects should be database-bound
        self.assertEqual(list(chris.edited.values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_foreign_key_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEqual(chris._state.db, None)
        self.assertEqual(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use 'other'...
        dive.editor = chris
        html5.editor = mark
        self.assertEqual(chris._state.db, 'other')
        self.assertEqual(html5._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(Person.objects.using('other').values_list('name',flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                           [u'Dive into Python'])

        # When saved (no using required), new objects goes to 'other'
        chris.save()
        html5.save()
        self.assertEqual(list(Person.objects.using('default').values_list('name',flat=True)),
                          [u'Marty Alchin'])
        self.assertEqual(list(Person.objects.using('other').values_list('name',flat=True)),
                          [u'Chris Mills', u'Mark Pilgrim'])
        self.assertEqual(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python'])

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEqual(water._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python'])

        # When saved, the new book goes to 'other'
        water.save()
        self.assertEqual(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEqual(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python', u'Dive into Water'])

    def test_foreign_key_validation(self):
        "ForeignKey.validate() uses the correct database"
        mickey = Person.objects.using('other').create(name="Mickey")
        pluto = Pet.objects.using('other').create(name="Pluto", owner=mickey)
        self.assertEqual(None, pluto.full_clean())

    def test_o2o_separation(self):
        "OneToOne fields are constrained to a single database"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')
        alice_profile = UserProfile.objects.using('default').create(user=alice, flavor='chocolate')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')
        bob_profile = UserProfile.objects.using('other').create(user=bob, flavor='crunchy frog')

        # Retrieve related objects; queries should be database constrained
        alice = User.objects.using('default').get(username="alice")
        self.assertEqual(alice.userprofile.flavor, "chocolate")

        bob = User.objects.using('other').get(username="bob")
        self.assertEqual(bob.userprofile.flavor, "crunchy frog")

        # Reget the objects to clear caches
        alice_profile = UserProfile.objects.using('default').get(flavor='chocolate')
        bob_profile = UserProfile.objects.using('other').get(flavor='crunchy frog')

        # Retrive related object by descriptor. Related objects should be database-baound
        self.assertEqual(alice_profile.user.username, 'alice')
        self.assertEqual(bob_profile.user.username, 'bob')

    def test_o2o_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        # Set a one-to-one relation with an object from a different database
        alice_profile = UserProfile.objects.using('default').create(user=alice, flavor='chocolate')
        try:
            bob.userprofile = alice_profile
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        bob_profile = UserProfile.objects.using('other').create(user=bob, flavor='crunchy frog')

        new_bob_profile = UserProfile(flavor="spring surprise")
        new_bob_profile.save(using='other')

        charlie = User(username='charlie',email='charlie@example.com')
        charlie.set_unusable_password()
        charlie.save(using='other')

        # old object comes from 'other', so the new object is set to use 'other'...
        new_bob_profile.user = bob
        charlie.userprofile = bob_profile
        self.assertEqual(new_bob_profile._state.db, 'other')
        self.assertEqual(charlie._state.db, 'other')

        # When saved (no using required), new objects goes to 'other'
        bob_profile.save()
        self.assertEqual(list(User.objects.using('default').values_list('username',flat=True)),
                          [u'alice'])
        self.assertEqual(list(User.objects.using('other').values_list('username',flat=True)),
                          [u'bob', u'charlie'])
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor',flat=True)),
                           [u'chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor',flat=True)),
                           [u'crunchy frog', u'spring surprise'])

        # This also works if you assign the O2O relation in the constructor
        denise = User.objects.db_manager('other').create_user('denise','denise@example.com')
        denise_profile = UserProfile(flavor="tofu", user=denise)

        self.assertEqual(denise_profile._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor',flat=True)),
                           [u'chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor',flat=True)),
                           [u'crunchy frog', u'spring surprise'])

        # When saved, the new profile goes to 'other'
        denise_profile.save()
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor',flat=True)),
                           [u'chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor',flat=True)),
                           [u'crunchy frog', u'spring surprise', u'tofu'])

    def test_ordering(self):
        "get_next_by_XXX commands stick to a single database"
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        learn = Book.objects.using('other').create(title="Learning Python",
                                                   published=datetime.date(2008, 7, 16))

        self.assertEqual(learn.get_next_by_published().title, "Dive into Python")
        self.assertEqual(dive.get_previous_by_published().title, "Learning Python")

    def test_subquery(self):
        """Make sure as_sql works with subqueries and master/slave."""
        sub = Person.objects.using('other').filter(name='fff')
        qs = Book.objects.filter(editor__in=sub)

        # When you call __str__ on the query object, it doesn't know about using
        # so it falls back to the default. If the subquery explicitly uses a
        # different database, an error should be raised.
        self.assertRaises(ValueError, str, qs.query)

        # Evaluating the query shouldn't work, either
        try:
            for obj in qs:
                pass
            self.fail('Iterating over query should raise DatabaseError')
        except DatabaseError:
            pass

    def test_related_manager(self):
        "Related managers return managers, not querysets"
        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # extra_arg is removed by the BookManager's implementation of
        # create(); but the BookManager's implementation won't get called
        # unless edited returns a Manager, not a queryset
        mark.edited.create(title="Dive into Water",
                           published=datetime.date(2009, 5, 4),
                           extra_arg=True)

        mark.edited.get_or_create(title="Dive into Water",
                                  published=datetime.date(2009, 5, 4),
                                  extra_arg=True)

class TestRouter(object):
    # A test router. The behaviour is vaguely master/slave, but the
    # databases aren't assumed to propagate changes.
    def db_for_read(self, model, instance=None, **hints):
        if instance:
            return instance._state.db or 'other'
        return 'other'

    def db_for_write(self, model, **hints):
        return DEFAULT_DB_ALIAS

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db in ('default', 'other') and obj2._state.db in ('default', 'other')

    def allow_syncdb(self, db, model):
        return True

class AuthRouter(object):
    """A router to control all database operations on models in
    the contrib.auth application"""

    def db_for_read(self, model, **hints):
        "Point all read operations on auth models to 'default'"
        if model._meta.app_label == 'auth':
            # We use default here to ensure we can tell the difference
            # between a read request and a write request for Auth objects
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on auth models to 'other'"
        if model._meta.app_label == 'auth':
            return 'other'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a model in Auth is involved"
        if obj1._meta.app_label == 'auth' or obj2._meta.app_label == 'auth':
            return True
        return None

    def allow_syncdb(self, db, model):
        "Make sure the auth app only appears on the 'other' db"
        if db == 'other':
            return model._meta.app_label == 'auth'
        elif model._meta.app_label == 'auth':
            return False
        return None

class WriteRouter(object):
    # A router that only expresses an opinion on writes
    def db_for_write(self, model, **hints):
        return 'writer'

class RouterTestCase(TestCase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [TestRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_db_selection(self):
        "Check that querysets obey the router for db suggestions"
        self.assertEqual(Book.objects.db, 'other')
        self.assertEqual(Book.objects.all().db, 'other')

        self.assertEqual(Book.objects.using('default').db, 'default')

        self.assertEqual(Book.objects.db_manager('default').db, 'default')
        self.assertEqual(Book.objects.db_manager('default').all().db, 'default')

    def test_syncdb_selection(self):
        "Synchronization behaviour is predicatable"

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertTrue(router.allow_syncdb('other', Book))

        # Add the auth router to the chain.
        # TestRouter is a universal synchronizer, so it should have no effect.
        router.routers = [TestRouter(), AuthRouter()]

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertTrue(router.allow_syncdb('other', Book))

        # Now check what happens if the router order is the other way around
        router.routers = [AuthRouter(), TestRouter()]

        self.assertFalse(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertFalse(router.allow_syncdb('other', Book))

    def test_partial_router(self):
        "A router can choose to implement a subset of methods"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        # First check the baseline behaviour

        self.assertEqual(router.db_for_read(User), 'other')
        self.assertEqual(router.db_for_read(Book), 'other')

        self.assertEqual(router.db_for_write(User), 'default')
        self.assertEqual(router.db_for_write(Book), 'default')

        self.assertTrue(router.allow_relation(dive, dive))

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        router.routers = [WriteRouter(), AuthRouter(), TestRouter()]

        self.assertEqual(router.db_for_read(User), 'default')
        self.assertEqual(router.db_for_read(Book), 'other')

        self.assertEqual(router.db_for_write(User), 'writer')
        self.assertEqual(router.db_for_write(Book), 'writer')

        self.assertTrue(router.allow_relation(dive, dive))

        self.assertFalse(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))


    def test_database_routing(self):
        marty = Person.objects.using('default').create(name="Marty Alchin")
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16),
                                                   editor=marty)
        pro.authors = [marty]

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        # An update query will be routed to the default database
        Book.objects.filter(title='Pro Django').update(pages=200)

        try:
            # By default, the get query will be directed to 'other'
            Book.objects.get(title='Pro Django')
            self.fail("Shouldn't be able to find the book")
        except Book.DoesNotExist:
            pass

        # But the same query issued explicitly at a database will work.
        pro = Book.objects.using('default').get(title='Pro Django')

        # Check that the update worked.
        self.assertEqual(pro.pages, 200)

        # An update query with an explicit using clause will be routed
        # to the requested database.
        Book.objects.using('other').filter(title='Dive into Python').update(pages=300)
        self.assertEqual(Book.objects.get(title='Dive into Python').pages, 300)

        # Related object queries stick to the same database
        # as the original object, regardless of the router
        self.assertEqual(pro.editor.name, u'Marty Alchin')

        # get_or_create is a special case. The get needs to be targetted at
        # the write database in order to avoid potential transaction
        # consistency problems
        book, created = Book.objects.get_or_create(title="Pro Django")
        self.assertFalse(created)

        book, created = Book.objects.get_or_create(title="Dive Into Python",
                                                   defaults={'published':datetime.date(2009, 5, 4)})
        self.assertTrue(created)

        # Check the head count of objects
        self.assertEqual(Book.objects.using('default').count(), 2)
        self.assertEqual(Book.objects.using('other').count(), 1)
        # If a database isn't specified, the read database is used
        self.assertEqual(Book.objects.count(), 1)

        # A delete query will also be routed to the default database
        Book.objects.filter(pages__gt=150).delete()

        # The default database has lost the book.
        self.assertEqual(Book.objects.using('default').count(), 1)
        self.assertEqual(Book.objects.using('other').count(), 1)

    def test_foreign_key_cross_database_protection(self):
        "Foreign keys can cross databases if they two databases have a common source"
        # Create a book and author on the default database
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('default').create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEqual(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Assignment implies a save, so database assignments of original objects have changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')
        self.assertEqual(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Add implies a save, so database assignments of original objects have changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')
        self.assertEqual(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')

        # If you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEqual(chris._state.db, None)
        self.assertEqual(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use the
        # source of 'other'...
        self.assertEqual(dive._state.db, 'other')
        dive.editor = chris
        html5.editor = mark

        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')
        self.assertEqual(chris._state.db, 'default')
        self.assertEqual(html5._state.db, 'default')

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEqual(water._state.db, 'default')

        # If you create an object through a FK relation, it will be
        # written to the write database, even if the original object
        # was on the read database
        cheesecake = mark.edited.create(title='Dive into Cheesecake', published=datetime.date(2010, 3, 15))
        self.assertEqual(cheesecake._state.db, 'default')

        # Same goes for get_or_create, regardless of whether getting or creating
        cheesecake, created = mark.edited.get_or_create(title='Dive into Cheesecake', published=datetime.date(2010, 3, 15))
        self.assertEqual(cheesecake._state.db, 'default')

        puddles, created = mark.edited.get_or_create(title='Dive into Puddles', published=datetime.date(2010, 3, 15))
        self.assertEqual(puddles._state.db, 'default')

    def test_o2o_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        # Set a one-to-one relation with an object from a different database
        alice_profile = UserProfile.objects.create(user=alice, flavor='chocolate')
        try:
            bob.userprofile = alice_profile
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(alice._state.db, 'default')
        self.assertEqual(alice_profile._state.db, 'default')
        self.assertEqual(bob._state.db, 'other')

        # ... but they will when the affected object is saved.
        bob.save()
        self.assertEqual(bob._state.db, 'default')

class AuthTestCase(TestCase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [AuthRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_auth_manager(self):
        "The methods on the auth manager obey database hints"
        # Create one user using default allocation policy
        User.objects.create_user('alice', 'alice@example.com')

        # Create another user, explicitly specifying the database
        User.objects.db_manager('default').create_user('bob', 'bob@example.com')

        # The second user only exists on the other database
        alice = User.objects.using('other').get(username='alice')

        self.assertEqual(alice.username, 'alice')
        self.assertEqual(alice._state.db, 'other')

        self.assertRaises(User.DoesNotExist, User.objects.using('default').get, username='alice')

        # The second user only exists on the default database
        bob = User.objects.using('default').get(username='bob')

        self.assertEqual(bob.username, 'bob')
        self.assertEqual(bob._state.db, 'default')

        self.assertRaises(User.DoesNotExist, User.objects.using('other').get, username='bob')

        # That is... there is one user on each database
        self.assertEqual(User.objects.using('default').count(), 1)
        self.assertEqual(User.objects.using('other').count(), 1)

    def test_dumpdata(self):
        "Check that dumpdata honors allow_syncdb restrictions on the router"
        User.objects.create_user('alice', 'alice@example.com')
        User.objects.db_manager('default').create_user('bob', 'bob@example.com')

        # Check that dumping the default database doesn't try to include auth
        # because allow_syncdb prohibits auth on default
        new_io = StringIO()
        try:
            management.call_command('dumpdata', 'auth', format='json', database='default', stdout=new_io)
        except:
            import traceback; traceback.print_exc()
            raise
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, '[]')

        # Check that dumping the other database does include auth
        new_io = StringIO()
        management.call_command('dumpdata', 'auth', format='json', database='other', stdout=new_io)
        command_output = new_io.getvalue().strip()
        self.assertTrue('"email": "alice@example.com",' in command_output)

_missing = object()
class UserProfileTestCase(TestCase):
    def setUp(self):
        self.old_auth_profile_module = getattr(settings, 'AUTH_PROFILE_MODULE', _missing)
        settings.AUTH_PROFILE_MODULE = 'multiple_database.UserProfile'

    def tearDown(self):
        if self.old_auth_profile_module is _missing:
            del settings.AUTH_PROFILE_MODULE
        else:
            settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def test_user_profiles(self):

        alice = User.objects.create_user('alice', 'alice@example.com')
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        alice_profile = UserProfile(user=alice, flavor='chocolate')
        alice_profile.save()

        bob_profile = UserProfile(user=bob, flavor='crunchy frog')
        bob_profile.save()

        self.assertEqual(alice.get_profile().flavor, 'chocolate')
        self.assertEqual(bob.get_profile().flavor, 'crunchy frog')

class AntiPetRouter(object):
    # A router that only expresses an opinion on syncdb,
    # passing pets to the 'other' database

    def allow_syncdb(self, db, model):
        "Make sure the auth app only appears on the 'other' db"
        if db == 'other':
            return model._meta.object_name == 'Pet'
        else:
            return model._meta.object_name != 'Pet'
        return None

class FixtureTestCase(TestCase):
    multi_db = True
    fixtures = ['multidb-common', 'multidb']

    def setUp(self):
        # Install the anti-pet router
        self.old_routers = router.routers
        router.routers = [AntiPetRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_fixture_loading(self):
        "Multi-db fixtures are loaded correctly"
        # Check that "Pro Django" exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        # Check that "Dive into Python" exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

        # Check that "Definitive Guide" exists on the both databases
        try:
            Book.objects.get(title="The Definitive Guide to Django")
            Book.objects.using('default').get(title="The Definitive Guide to Django")
            Book.objects.using('other').get(title="The Definitive Guide to Django")
        except Book.DoesNotExist:
            self.fail('"The Definitive Guide to Django" should exist on both databases')

    def test_pseudo_empty_fixtures(self):
        "A fixture can contain entries, but lead to nothing in the database; this shouldn't raise an error (ref #14068)"
        new_io = StringIO()
        management.call_command('loaddata', 'pets', stdout=new_io, stderr=new_io)
        command_output = new_io.getvalue().strip()
        # No objects will actually be loaded
        self.assertEqual(command_output, "Installed 0 object(s) (of 2) from 1 fixture(s)")

class PickleQuerySetTestCase(TestCase):
    multi_db = True

    def test_pickling(self):
        for db in connections:
            Book.objects.using(db).create(title='Dive into Python', published=datetime.date(2009, 5, 4))
            qs = Book.objects.all()
            self.assertEqual(qs.db, pickle.loads(pickle.dumps(qs)).db)


class DatabaseReceiver(object):
    """
    Used in the tests for the database argument in signals (#13552)
    """
    def __call__(self, signal, sender, **kwargs):
        self._database = kwargs['using']

class WriteToOtherRouter(object):
    """
    A router that sends all writes to the other database.
    """
    def db_for_write(self, model, **hints):
        return "other"

class SignalTests(TestCase):
    multi_db = True

    def setUp(self):
        self.old_routers = router.routers

    def tearDown(self):
        router.routser = self.old_routers

    def _write_to_other(self):
        "Sends all writes to 'other'."
        router.routers = [WriteToOtherRouter()]

    def _write_to_default(self):
        "Sends all writes to the default DB"
        router.routers = self.old_routers

    def test_database_arg_save_and_delete(self):
        """
        Tests that the pre/post_save signal contains the correct database.
        (#13552)
        """
        # Make some signal receivers
        pre_save_receiver = DatabaseReceiver()
        post_save_receiver = DatabaseReceiver()
        pre_delete_receiver = DatabaseReceiver()
        post_delete_receiver = DatabaseReceiver()
        # Make model and connect receivers
        signals.pre_save.connect(sender=Person, receiver=pre_save_receiver)
        signals.post_save.connect(sender=Person, receiver=post_save_receiver)
        signals.pre_delete.connect(sender=Person, receiver=pre_delete_receiver)
        signals.post_delete.connect(sender=Person, receiver=post_delete_receiver)
        p = Person.objects.create(name='Darth Vader')
        # Save and test receivers got calls
        p.save()
        self.assertEqual(pre_save_receiver._database, DEFAULT_DB_ALIAS)
        self.assertEqual(post_save_receiver._database, DEFAULT_DB_ALIAS)
        # Delete, and test
        p.delete()
        self.assertEqual(pre_delete_receiver._database, DEFAULT_DB_ALIAS)
        self.assertEqual(post_delete_receiver._database, DEFAULT_DB_ALIAS)
        # Save again to a different database
        p.save(using="other")
        self.assertEqual(pre_save_receiver._database, "other")
        self.assertEqual(post_save_receiver._database, "other")
        # Delete, and test
        p.delete(using="other")
        self.assertEqual(pre_delete_receiver._database, "other")
        self.assertEqual(post_delete_receiver._database, "other")

class AttributeErrorRouter(object):
    "A router to test the exception handling of ConnectionRouter"
    def db_for_read(self, model, **hints):
        raise AttributeError

    def db_for_write(self, model, **hints):
        raise AttributeError

class RouterAttributeErrorTestCase(TestCase):
    multi_db = True

    def setUp(self):
        self.old_routers = router.routers
        router.routers = [AttributeErrorRouter()]

    def tearDown(self):
        router.routers = self.old_routers

    def test_attribute_error_read(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        router.routers = [] # Reset routers so we can save a Book instance
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        router.routers = [AttributeErrorRouter()] # Install our router
        self.assertRaises(AttributeError, Book.objects.get, pk=b.pk)

    def test_attribute_error_save(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        self.assertRaises(AttributeError, dive.save)

    def test_attribute_error_delete(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        router.routers = [] # Reset routers so we can save our Book, Person instances
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        p = Person.objects.create(name="Marty Alchin")
        b.authors = [p]
        b.editor = p
        router.routers = [AttributeErrorRouter()] # Install our router
        self.assertRaises(AttributeError, b.delete)

class ModelMetaRouter(object):
    "A router to ensure model arguments are real model classes"
    def db_for_write(self, model, **hints):
        if not hasattr(model, '_meta'):
            raise ValueError

class RouterModelArgumentTestCase(TestCase):
    multi_db = True

    def setUp(self):
        self.old_routers = router.routers
        router.routers = [ModelMetaRouter()]

    def tearDown(self):
        router.routers = self.old_routers

    def test_foreignkey_collection(self):
        person = Person.objects.create(name='Bob')
        pet = Pet.objects.create(owner=person, name='Wart')
        # test related FK collection
        person.delete()
