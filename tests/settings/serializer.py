from django_mongodb_engine.creation import DatabaseCreation
from django.core.serializers.json import \
    Serializer, Deserializer as JSONDeserializer


def get_objectid_fields(modelopts, typemap=DatabaseCreation.data_types):
    return [field for field in modelopts.fields if
            typemap.get(field.__class__.__name__) == 'key']


def Deserializer(*args, **kwargs):
    for objwrapper in JSONDeserializer(*args, **kwargs):
        obj = objwrapper.object
        for field in get_objectid_fields(obj._meta):
            value = getattr(obj, field.attname)
            try:
                int(value)
            except (TypeError, ValueError):
                pass
            else:
                setattr(obj, field.attname, int_to_objectid(value))
        yield objwrapper


def int_to_objectid(i):
    return str(i).rjust(24, '0')
