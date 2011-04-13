from django.core.serializers.base import Serializer
from django.core.serializers.json import Deserializer as JSONDeserializer

def Deserializer(*args, **kwargs):
    for objwrapper in JSONDeserializer(*args, **kwargs):
        obj = objwrapper.object
        try:
            int(obj.id)
        except ValueError:
            pass
        else:
            obj.id = int_to_objectid(obj.id)
        yield objwrapper

def int_to_objectid(i):
    return str(i).rjust(24, '0')
