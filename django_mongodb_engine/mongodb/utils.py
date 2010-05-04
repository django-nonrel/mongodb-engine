from django.utils.functional import SimpleLazyObject

def dict_keys_to_str(dictionary, recursive=False):
    return dict([(str(k), (not isinstance(v, dict) and v) or (recursive and dict_keys_to_str(v)) or v) for k,v in dictionary.items()])

class ModelLazyObject(SimpleLazyObject):
    """
    A lazy object initialised a model.
    """
    def __init__(self, model, pk):
        """
        Pass in a callable that returns the object to be wrapped.

        If copies are made of the resulting SimpleLazyObject, which can happen
        in various circumstances within Django, then you must ensure that the
        callable can be safely run more than once and will return the same
        value.
        """
        # For some reason, we have to inline LazyObject.__init__ here to avoid
        # recursion
        self._wrapped = None
        self.__dict__['_pk'] = pk
        self.__dict__['_model'] = model
        super(ModelLazyObject, self).__init__(self._load_data)

    def _load_data(self):
        return self._model.objects.get(pk=self._pk)
