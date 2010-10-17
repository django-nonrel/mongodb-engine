"""
Test suite for django-mongodb-engine.
"""
from django.test import TestCase
from testproj.myapp.models import Entry, Blog, StandardAutoFieldModel, Person, TestFieldModel, DynamicModel
import datetime
from pymongo.objectid import ObjectId

class MongoDjTest(TestCase):
    multi_db = True

    def test_add_and_delete_blog(self):
        blog1 = Blog(title="blog1")
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        blog2 = Blog(title="blog2")
        self.assertEqual(blog2.pk, None)
        blog2.save()
        self.assertNotEqual(blog2.pk, None)
        self.assertEqual(Blog.objects.count(), 2)
        blog2.delete()
        self.assertEqual(Blog.objects.count(), 1)
        blog1.delete()
        self.assertEqual(Blog.objects.count(), 0)

    def test_simple_get(self):
        blog1 = Blog(title="blog1")
        blog1.save()
        blog2 = Blog(title="blog2")
        blog2.save()
        self.assertEqual(Blog.objects.count(), 2)
        self.assertEqual(
            Blog.objects.get(title="blog2"),
            blog2
        )
        self.assertEqual(
            Blog.objects.get(title="blog1"),
            blog1
        )

    def test_simple_filter(self):
        blog1 = Blog(title="same title")
        blog1.save()
        blog2 = Blog(title="same title")
        blog2.save()
        blog3 = Blog(title="another title")
        blog3.save()
        self.assertEqual(Blog.objects.count(), 3)
        self.assertEqual(Blog.objects.get(pk=blog1.pk), blog1)
        self.assertEqual(
            Blog.objects.filter(title="same title").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title="same title", pk=blog1.pk).count(),
            1
        )
        self.assertEqual(
            Blog.objects.filter(title__startswith="same").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__istartswith="SAME").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__endswith="title").count(),
            3
        )
        self.assertEqual(
            Blog.objects.filter(title__iendswith="Title").count(),
            3
        )
        self.assertEqual(
            Blog.objects.filter(title__icontains="same").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__contains="same").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__iexact="same Title").count(),
            2
        )

        self.assertEqual(
            Blog.objects.filter(title__regex="s.me.*").count(),
            2
        )
        self.assertEqual(
            Blog.objects.filter(title__iregex="S.me.*").count(),
            2
        )

    def test_change_model(self):
        blog1 = Blog(title="blog 1")
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        blog1.title = "new title"
        blog1.save()
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(blog1.title, Blog.objects.all()[0].title)

    def test_dates_ordering(self):
        now = datetime.datetime.now()
        before = now - datetime.timedelta(days=1)

        entry1 = Entry(title="entry 1", date_published=now)
        entry1.save()

        entry2 = Entry(title="entry 2", date_published=before)
        entry2.save()

        self.assertEqual(
            list(Entry.objects.order_by('-date_published')),
            [entry1, entry2]
        )

        self.assertEqual(
            list(Entry.objects.order_by('date_published')),
            [entry2, entry1]
        )


    def test_dates_less_and_more_than(self):
        now = datetime.datetime.now()
        before = now + datetime.timedelta(days=1)
        after = now - datetime.timedelta(days=1)

        entry1 = Entry(title="entry 1", date_published=now)
        entry1.save()

        entry2 = Entry(title="entry 2", date_published=before)
        entry2.save()

        entry3 = Entry(title="entry 3", date_published=after)
        entry3.save()

        a = list(Entry.objects.filter(date_published=now))
        self.assertEqual(
            list(Entry.objects.filter(date_published=now)),
            [entry1]
        )
        self.assertEqual(
            list(Entry.objects.filter(date_published__lt=now)),
            [entry3]
        )
        self.assertEqual(
            list(Entry.objects.filter(date_published__gt=now)),
            [entry2]
        )
    def test_complex_queries(self):
        p1 = Person(name="igor", surname="duck", age=39)
        p1.save()
        p2 = Person(name="andrea", surname="duck", age=29)
        p2.save()
        self.assertEqual(
            Person.objects.filter(name="igor", surname="duck").count(),
            1
        )
        self.assertEqual(
            Person.objects.filter(age__gte=20, surname="duck").count(),
            2
        )

    def test_fields(self):
        t1 = TestFieldModel(title="p1",
                            mlist=["ab", {'a':23, "b":True  }],
                            slist=["bc", "ab"],
                            mdict = {'a':23, "b":True  },
                            mset=["a", 'b', "b"]
                            )
        t1.save()

        t = TestFieldModel.objects.get(id=t1.id)
        self.assertEqual(t.mlist, ["ab", {'a':23, "b":True  }])
        self.assertEqual(t.mlist_default, ["a", "b"])
        self.assertEqual(t.slist, ["ab", "bc"])
        self.assertEqual(t.slist_default, ["a", "b"])
        self.assertEqual(t.mdict, {'a':23, "b":True  })
        self.assertEqual(t.mdict_default, {"a": "a", 'b':1})
        self.assertEqual(sorted(t.mset), ["a", 'b'])
        self.assertEqual(sorted(t.mset_default), ["a", 'b'])

        from django_mongodb_engine.query import A
        t2 = TestFieldModel.objects.get(mlist=A("a", 23))
        self.assertEqual(t1.pk, t2.pk)

    def test_simple_foreign_keys(self):
        now = datetime.datetime.now()

        blog1 = Blog(title="Blog")
        blog1.save()
        entry1 = Entry(title="entry 1", blog=blog1)
        entry1.save()
        entry2 = Entry(title="entry 2", blog=blog1)
        entry2.save()
        self.assertEqual(Entry.objects.count(), 2)

        for entry in Entry.objects.all():
            self.assertEqual(
                blog1,
                entry.blog
            )

        blog2 = Blog(title="Blog")
        blog2.save()
        entry3 = Entry(title="entry 3", blog=blog2)
        entry3.save()
        self.assertEqual(
            # it's' necessary to explicitly state the pk here
            list(Entry.objects.filter(blog=blog1.pk)),
            [entry1, entry2]
        )


    def test_foreign_keys_bug(self):
        blog1 = Blog(title="Blog")
        blog1.save()
        entry1 = Entry(title="entry 1", blog=blog1)
        entry1.save()
        self.assertEqual(
            # this should work too
            list(Entry.objects.filter(blog=blog1)),
            [entry1]
        )

    def test_standard_autofield(self):

        sam1 = StandardAutoFieldModel(title="title 1")
        sam1.save()
        sam2 = StandardAutoFieldModel(title="title 2")
        sam2.save()

        self.assertEqual(
            StandardAutoFieldModel.objects.count(),
            2
        )

        sam1_query = StandardAutoFieldModel.objects.get(title="title 1")
        self.assertEqual(
            sam1_query.pk,
            sam1.pk
        )

        sam1_query = StandardAutoFieldModel.objects.get(pk=sam1.pk)


    def test_generic_field(self):

        dyn = DynamicModel(gen=u"title 1")
        dyn.save()

        dyn = DynamicModel.objects.get(gen=u"title 1")


        self.assertTrue(isinstance(
            dyn.gen,
            unicode
        ))

        dyn.gen = 1
        dyn.save()
        dyn = DynamicModel.objects.get(gen=1)

        self.assertTrue(isinstance(
            dyn.gen,
            int
        ))

        dyn.gen = { "type" : "This is a dict"}
        dyn.save()
        dyn = DynamicModel.objects.get(gen={ "type" : "This is a dict"})

        self.assertTrue(isinstance(
            dyn.gen,
            dict
        ))


    def test_update(self):
        blog1 = Blog(title="Blog")
        blog1.save()
        blog2 = Blog(title="Blog 2")
        blog2.save()
        entry1 = Entry(title="entry 1", blog=blog1)
        entry1.save()

        Entry.objects.filter(pk=entry1.pk).update(blog=blog2)

        self.assertEqual(
            # this should work too
            list(Entry.objects.filter(blog=blog2)),
            [entry1]
        )


        Entry.objects.filter(blog=blog2).update(title="Title has been updated")

        self.assertEqual(
            # this should work too
            Entry.objects.filter()[0].title,
            "Title has been updated"
        )

        Entry.objects.filter(blog=blog2).update(title="Last Update Test", blog=blog1)

        self.assertEqual(
            # this should work too
            Entry.objects.filter()[0].title,
            "Last Update Test"
        )

        self.assertEqual(
            # this should work too
            Entry.objects.filter(blog=blog1).count(),
            1
        )

    def test_update_id(self):
        Entry.objects.filter(title='Last Update Test').update(id=ObjectId())
