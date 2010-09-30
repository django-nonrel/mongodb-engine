import os
os.environ["DJANGO_SETTINGS_MODULE"] = "testproj.settings"

from myapp.models import Entry, Person

entry, c = Entry.objects.get_or_create(title="Ciao")
print Entry.objects.filter(blog__isnull=True)

doc, c = Person.mongodb.get_or_create(name="Pippo", defaults={'surname' : "Pluto", 'age' : 10})
print doc.pk
print doc.surname
print doc.age

cursor = Person.mongodb.filter(age=10)
print cursor[0]