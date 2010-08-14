========================
 Django MongoDB Engine
========================
:Version: 0.1.1
:Info: It's a database backend that adds mongodb support to django
:Author: Flavio [FlaPer87] Percoco Premoli (http://github.com/FlaPer87) and Alberto [aparo] Paro (http://github.com/aparo)
:Web: http://github.com/FlaPer87/django-mongodb-engine/
:Download: http://pypi.python.org/pypi/django_mongodb_engine/
:Source: http://github.com/FlaPer87/django-mongodb-engine/
:Keywords: django, mongodb, orm, nosql, database, python

Requirements
============

- Django non rel http://github.com/aparo/django-nonrel
- Djangotoolbox http://github.com/aparo/djangotoolbox or http://bitbucket.org/wkornewald/djangotoolbox
    
Infographics
============
::

    - Django Nonrel branch
    - Manager
    - Compiler (MongoDB Engine one)
    - MongoDB

django-mongodb-engine uses the new django1.2 multi-database support and sets to the model the database using the "django_mongodb_engine.mongodb".

Examples
========
For detailed examples see: (http://github.com/FlaPer87/django-mongodb-engine/tree/master/tests/testproj/)
::

    class Person(models.Model):
        name = models.CharField(max_length=20)
        surname = models.CharField(max_length=20)
        age = models.IntegerField(null=True, blank=True)
                
        def __unicode__(self):
            return u"Person: %s %s" % (self.name, self.surname)

    >> p, created = Person.objects.get_or_create(name="John", defaults={'surname' : 'Doe'})
    >> print created
    True
    >> p.age = 22
    >> p.save()

    === Querying ===
    >> p = Person.objects.get(name__istartswith="JOH", age=22)
    >> p.pk
    u'4bd212d9ccdec2510f000000'


Bug tracker
===========

If you have any suggestions, bug reports or annoyances please report them
to our issue tracker at http://github.com/FlaPer87/django-mongodb-engine/issues/

Wiki
====

http://wiki.github.com/FlaPer87/django-mongodb-engine/

Contributing
============

Development of ``django-mongodb-engine`` happens at Github: http://github.com/FlaPer87/django-mongodb-engine/

You are highly encouraged to participate in the development
of ``django-mongodb-engine``. If you don't like Github (for some reason) you're welcome
to send regular patches.

License
=======

This software is licensed under the ``New BSD License``. See the ``LICENSE``
file in the top distribution directory for the full license text.

.. # vim: syntax=rst expandtab tabstop=4 shiftwidth=4 shiftround
