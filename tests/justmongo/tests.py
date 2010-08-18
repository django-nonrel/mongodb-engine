import os
os.environ["DJANGO_SETTINGS_MODULE"] = "justmongo.settings"

from django.db.models import signals
from django.contrib.auth.models import User
from myapp.models import Entry, Person

my_user, created = User.objects.get_or_create(username="tester", defaults={})
print my_user.pk
my_user.set_password("TEST_PASSWORD")
my_user.save()

