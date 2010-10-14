from pymongo import Connection
from pymongo.objectid import ObjectId
from pymongo.son_manipulator import SONManipulator

from django.db.models import Model
from django.contrib.contenttypes.models import ContentType
from django.utils.importlib import import_module

from datetime import datetime, date, time

#TODO Add content type cache
from .utils import ModelLazyObject

class TransformDjango(SONManipulator):

    def encode_django(self, model, collection):
        """
        Encode ricorsive embedded models and django models
        """
        # If we get here is because model instance has to be related.
        model.save()
        return {'_app':model._meta.app_label, 
                '_model':model._meta.module_name,
                'pk':model.pk,
                '_type':"django"}
    
    def transform_incoming(self, son, collection):
        if isinstance(son, dict):
            for (key, value) in son.items():
                if isinstance(value, (str, unicode)):
                    continue
                if isinstance(value, Model):
                    son[key] = self.encode_django(value, collection)
                elif isinstance(value, dict): # Make sure we recurse into sub-docs
                    son[key] = self.transform_incoming(value, collection)
                elif hasattr(value, "__iter__"): # Make sure we recurse into sub-docs
                    son[key] = [self.transform_incoming(item, collection) for item in value]
        elif isinstance(son, (str, unicode)):
            pass
        elif hasattr(son, "__iter__"): # Make sure we recurse into sub-docs
            son = [self.transform_incoming(item, collection) for item in son]
        return son

    def decode_django(self, data, collection):
        if data['_type']=="django":
            model = ContentType.objects.get(app_label=data['_app'], model=data['_model'])
            return ModelLazyObject(model.model_class(), data['pk'])
    
    def transform_outgoing(self, son, collection):
        if isinstance(son, dict):
            if "_type" in son and son["_type"] in [u"django"]:
                son = self.decode_django(son, collection)
            else:
                for (key, value) in son.items():
                    if isinstance(value, dict):
                        if "_type" in value and value["_type"] in [u"django"]:
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
