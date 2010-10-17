from django.db import connections

class MapReduceResult(object):
    def __init__(self, model, object_id, reduce_value):
        self.model = model
        self.object_id = object_id
        self.value = reduce_value

    def get_object(self):
        return self.model.objects.get(id=self.object_id)

    def __repr__(self):
        return '<%s model=%r _id=%r value=%r>' % \
                (self.__class__.__name__, self.model, self.object_id, self.value)

# TODO:
# - Query support
# - Field name substitution (e.g. id -> _id)
class MapReduceMixin(object):
    def _get_collection(self):
        return connections[self.db].db_connection[self.model._meta.db_table]

    def map_reduce(self, map_func, reduce_func, finalize_func=None,
                   limit=None, scope=None, keeptemp=False):
        collection = self._get_collection()
        if not hasattr(collection, 'map_reduce'):
            raise NotImplementedError('map/reduce requires MongoDB >= 1.1.1')

        mapreduce_kwargs = {}
        if finalize_func is not None:
            mapreduce_kwargs['finalize'] = finalize_func
        if limit is not None:
            mapreduce_kwargs['limit'] = limit
        if scope is not None:
            mapreduce_kwargs['scope'] = scope

        mapreduce_kwargs['keeptemp'] = keeptemp

        result_collection = collection.map_reduce(map_func, reduce_func,
                                                  **mapreduce_kwargs)
        return [MapReduceResult(self.model, doc['_id'], doc['value'])
                for doc in result_collection.find()]
