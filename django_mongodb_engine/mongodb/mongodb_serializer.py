from pymongo import Connection
from pymongo.objectid import ObjectId
from pymongo.son_manipulator import SONManipulator

from django.utils.importlib import import_module

from datetime import datetime, date, time

#TODO Add content type cache
from .utils import ModelLazyObject

class TransformDjango(SONManipulator):

    def encode_django(self, model, collection):
        """
        Encode ricorsive embedded models and django models
        """
        from django_mongodb_engine.mongodb.fields import EmbeddedModel
        if isinstance(model, EmbeddedModel):
            if model.pk is None:
                model.pk = unicode(ObjectId())
            res = {'_app':model._meta.app_label,
                   '_model':model._meta.module_name,
                   '_id':model.pk}
            for field in model._meta.fields:
                res[field.attname] = self.transform_incoming(getattr(model, field.attname), collection)
            res["_type"] = "emb"
            from django.contrib.contenttypes.models import ContentType
            try:
                ContentType.objects.get(app_label=res['_app'], model=res['_model'])
            except:
                res['_app'] = model.__class__.__module__
                res['_model'] = model._meta.object_name

            return res
        if not model.pk:
            model.save()
        return {'_app':model._meta.app_label,
                '_model':model._meta.module_name,
                'pk':model.pk,
                '_type':"django"}

    def transform_incoming(self, son, collection):
        from django.db.models import Model
        from django_mongodb_engine.mongodb.fields import EmbeddedModel
        if isinstance(son, dict):
            for (key, value) in son.items():
                if isinstance(value, (str, unicode)):
                    continue
                if isinstance(value, (Model, EmbeddedModel)):
                    son[key] = self.encode_django(value, collection)
                elif isinstance(value, dict): # Make sure we recurse into sub-docs
                    son[key] = self.transform_incoming(value, collection)
                elif hasattr(value, "__iter__"): # Make sure we recurse into sub-docs
                    son[key] = [self.transform_incoming(item, collection) for item in value]
        elif isinstance(son, (str, unicode)):
            pass
        elif hasattr(son, "__iter__"): # Make sure we recurse into sub-docs
            son = [self.transform_incoming(item, collection) for item in son]
        elif isinstance(son, (Model, EmbeddedModel)):
            son = self.encode_django(son, collection)
        return son

    def decode_django(self, data, collection):
        from django.contrib.contenttypes.models import ContentType
        if data['_type']=="django":
            model = ContentType.objects.get(app_label=data['_app'], model=data['_model'])
            return ModelLazyObject(model.model_class(), data['pk'])
        elif data['_type']=="emb":
            try:
                model = ContentType.objects.get(app_label=data['_app'], model=data['_model']).model_class()
            except:
                module = import_module(data['_app'])
                model = getattr(module, data['_model'])

            del data['_type']
            del data['_app']
            del data['_model']
            data.pop('_id', None)
            values = {}
            for k,v in data.items():
                values[str(k)] = self.transform_outgoing(v, collection)
            return model(**values)

    def transform_outgoing(self, son, collection):
        if isinstance(son, dict):
            if "_type" in son and son["_type"] in [u"django", u'emb']:
                son = self.decode_django(son, collection)
            else:
                for (key, value) in son.items():
                    if isinstance(value, dict):
                        if "_type" in value and value["_type"] in [u"django", u'emb']:
                            son[key] = self.decode_django(value, collection)
                        else:
                            son[key] = self.transform_outgoing(value, collection)
                    elif hasattr(value, "__iter__"): # Make sure we recurse into sub-docs
                        son[key] = [self.transform_outgoing(item, collection) for item in value]
                    else: # Again, make sure to recurse into sub-docs
                        son[key] = self.transform_outgoing(value, collection)
        elif hasattr(son, "__iter__"): # Make sure we recurse into sub-docs
            son = [self.transform_outgoing(item, collection) for item in son]

        return son
