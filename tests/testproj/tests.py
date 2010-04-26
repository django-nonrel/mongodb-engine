import os
os.environ["DJANGO_SETTINGS_MODULE"] = "notsqltestproj.settings"

from myapp.models import Entry, Person

doc, c = Person.mongodb.get_or_create(name="Pippo", defaults={'surname' : "Pluto", 'age' : 10})
print doc.pk
print doc.surname
print doc.age

cursor = Person.mongodb.filter(age=10)
print cursor[0]