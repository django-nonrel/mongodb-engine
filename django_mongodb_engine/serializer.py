from django.db.models import Model
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import SimpleLazyObject
from pymongo.son_manipulator import SONManipulator

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
        if isinstance(value, (list, tuple, set)):
            return [self.transform_incoming(item, collection) for item in value]

        if isinstance(value, dict):
            return dict((key, self.transform_incoming(subvalue, collection))
                        for key, subvalue in value.iteritems())

        if isinstance(value, Model):
            value.save()
            return {
                '_app' : value._meta.app_label,
                '_model' : value._meta.app_label,
                'pk' : value.pk,
                '_type' : 'django'
            }

        return value

    def transform_outgoing(self, son, collection):
        if isinstance(son, (list, tuple, set)):
            return [self.transform_outgoing(value, collection) for value in son]

        if isinstance(son, dict):
            if son.get('_type') == 'django':
                model_class = get_model(son['_app'], son['_model']).model_class()
                return LazyModelInstance(model_class, son['pk'])

            else:
                return dict((key, self.transform_outgoing(value, collection))
                             for key, value in son.iteritems())
        return son
