from django.db import models

from .tokenizer import BaseTokenizer


__all__ = ['TokenizedField']


class TokenizedField(models.Field):

    def __init__(self, *args, **kwargs):
        super(TokenizedField, self).__init__(*args, **kwargs)
        as_textfield = kwargs.pop('as_textfield', False)
        self._tokenizer = kwargs.pop('tokenizer', BaseTokenizer)()
        self.parent_field = models.CharField(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TokenizedField, self).contribute_to_class(
            cls, '%s_tokenized' % name)
        setattr(self, 'parent_field_name', name)
        cls.add_to_class(name, self.parent_field)

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        # If for some reason value is being converted to list by some
        # internal processing we'll convert it back to string.
        # For Example: When using the 'in' lookup type.
        if isinstance(value, list):
            value = ''.join(value)

        # When 'exact' is used we'll perform an exact_phrase query
        # using the $all operator otherwhise we'll just tokenized
        # the value. Djangotoolbox will do the remaining checks.
        if lookup_type == 'exact':
            return {'$all': self._tokenizer.tokenize(value)}
        return self._tokenizer.tokenize(value)

    def pre_save(self, model_instance, add):
        return self._tokenizer.tokenize(getattr(model_instance,
                                                self.parent_field_name))
