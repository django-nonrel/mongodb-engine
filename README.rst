===========
Django MongoDB Engine
===========
:Info: It's a database backend that adds mongodb support to django
:Author: Flavio [FlaPer87] Percoco Premoli (http://github.com/FlaPer87) and Alberto [aparo] Paro (http://github.com/aparo)

Requirements
------------

- Django non rel http://github.com/aparo/django-nonrel
- Djangotoolbox http://github.com/aparo/djangotoolbox or http://bitbucket.org/wkornewald/djangotoolbox


About Django
============
Django is a high-level Python Web framework that encourages rapid development and clean, pragmatic design.

About MongoDB
=============
MongoDB bridges the gap between key-value stores (which are fast and highly scalable) and traditional RDBMS systems (which provide rich queries and deep functionality).

Installation
============
::

    pip install django_mongodb_engine
    
    
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
