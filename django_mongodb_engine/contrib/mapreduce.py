from django.db import connections

class MapReduceResult(object):
    """
    Represents one item of a MapReduce result array.

    :param model: the :class:``django.db.Model`` used to perform the MapReduce
    :param key: the *key* from the result item
    :param value: the *value* from the result item
    """
    def __init__(self, model, key, value):
        self.model = model
        self.key = key
        self.value = value

    def get_object(self):
        """
        Fetches the model instance with ``self.key`` as primary key from the
        database (doing a database query).
        """
        return self.model.objects.get(**{self.model._meta.pk.attname : self.key})

    def __repr__(self):
        return '<%s model=%r key=%r value=%r>' % \
                (self.__class__.__name__, self.model.__name__, self.key, self.value)

# TODO:
# - Query support
# - Field name substitution (e.g. id -> _id)
class MapReduceMixin(object):
    """
    Mixes MapReduce support into your manager.
    """
    def _get_collection(self):
        return connections[self.db].db_connection[self.model._meta.db_table]

    def map_reduce(self, map_func, reduce_func, finalize_func=None,
                   limit=None, scope=None, keeptemp=False):
        """
        Performs a MapReduce on the server using `map_func`, `reduce_func` and
        (optionally) `finalize_func`.

        Returns a list of :class:~MapReduceResult instances, one instance for
        each item in the array the MapReduce query returns.

        MongoDB *>= 1.1* and PyMongo *>= 1.2* are required for using this feature.

        :param map_func: JavaScript map function as string
        :param reduce_func: The JavaScript reduce function as string
        :param finalize_func: (optional) JavaScript finalize function as string
        :param limit: (optional) Number of entries to be processed
        :param scope: (optional) Variable scope to pass the functions
        :param keeptemp: Whether to keep the temporarily created collection
                         (boolean, defaults to :const:``False``)
        """
        collection = self._get_collection()

        if not hasattr(collection, 'map_reduce'):
            raise NotImplementedError('map/reduce requires MongoDB >= 1.1.1')

        mapreduce_kwargs = {'keeptemp' : keeptemp}

        if finalize_func is not None:
            mapreduce_kwargs['finalize'] = finalize_func
        if limit is not None:
            mapreduce_kwargs['limit'] = limit
        if scope is not None:
            mapreduce_kwargs['scope'] = scope

        result_collection = collection.map_reduce(map_func, reduce_func, **mapreduce_kwargs)
        return [MapReduceResult(self.model, doc['_id'], doc['value'])
                for doc in result_collection.find()]
