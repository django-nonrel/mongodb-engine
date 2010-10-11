try:
    from django import MODIFIED as modified_django
except ImportError:
    modified_django = False
from django.core import exceptions
from django.conf import settings
from django.db import models
from django.db.models.fields import AutoField as DjangoAutoField
from pymongo.objectid import ObjectId

if 'django_mongodb_engine' not in settings.INSTALLED_APPS:
    settings.INSTALLED_APPS.insert(0, 'django_mongodb_engine')


def AutoField_to_python(value):
    if value is None:
        return value
    try:
        return unicode(value)
    except (TypeError, ValueError):
        raise exceptions.ValidationError("Invalid AutoField value %r" % value)

def AutoField_get_prep_value(value):
    if value is None:
        return None
    return ObjectId(value)

def pre_init_mongodb_signal(sender, args, **kwargs):
    model = sender # may not use `model` directly as argument because of
                   # Django's magic arg inspecting voodoo
    if model._meta.abstract:
        return

    database_for_model = settings.DATABASES[model.objects.db]
    primary_key_field  = model._meta.pk

    if (
        'mongodb' in database_for_model['ENGINE']          # model doesn't use MongoDB backend
        and isinstance(primary_key_field, DjangoAutoField) # custom primary key
        and not modified_django                            # already patched Django version XXX
    ):
        # patch the default AutoField to make it ObjectId-compatible
        setattr(primary_key_field, 'to_python', AutoField_to_python)
        setattr(primary_key_field, 'get_prep_value', AutoField_get_prep_value)

models.signals.pre_init.connect(pre_init_mongodb_signal)
