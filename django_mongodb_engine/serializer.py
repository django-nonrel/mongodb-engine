from django.db import models
from django.db.models.query import QuerySet
from django.utils.functional import SimpleLazyObject
from django.utils.importlib import import_module
from pymongo.son_manipulator import SONManipulator

def get_model_by_meta(model_meta):
    app, model = model_meta['_app'], model_meta['_model']
    try:
        module = import_module(app + '.models')
    except ImportError:
        return models.get_model(app, model)
    else:
        try:
            return getattr(module, model)
        except AttributeError:
            raise AttributeError("Could not find model %r in module %r" % (model, module))

class LazyModelInstance(SimpleLazyObject):
    """
    Lazy model instance.
    """
    def __init__(self, model, pk):
        self.__dict__['_pk'] = pk
        self.__dict__['_model'] = model
        super(LazyModelInstance, self).__init__(self._load_data)

    def _load_data(self):
        return self._model.objects.get(pk=self._pk)

    def __eq__(self, other):
        if isinstance(other, LazyModelInstance):
            return self.__dict__['_pk'] == other.__dict__['_pk'] and \
                   self.__dict__['_model'] == other.__dict__['_model']
        return super(LazyModelInstance, self).__eq__(other)


class TransformDjango(SONManipulator):
    def transform_incoming(self, value, collection):
        if isinstance(value, (list, tuple, set, QuerySet)):
            return [self.transform_incoming(item, collection) for item in value]

        if isinstance(value, dict):
            return dict((key, self.transform_incoming(subvalue, collection))
                        for key, subvalue in value.iteritems())

        if isinstance(value, models.Model):
            value.save()
            return {
                '_app' : value._meta.app_label,
                '_model' : value._meta.object_name,
                'pk' : value.pk,
                '_type' : 'django'
            }

        return value

    def transform_outgoing(self, son, collection):
        if isinstance(son, (list, tuple, set)):
            return [self.transform_outgoing(value, collection) for value in son]

        if isinstance(son, dict):
            if son.get('_type') == 'django':
                return LazyModelInstance(get_model_by_meta(son), son['pk'])
            else:
                return dict((key, self.transform_outgoing(value, collection))
                             for key, value in son.iteritems())
        return son
