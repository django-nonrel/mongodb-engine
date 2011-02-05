from django.db import models
from .tokenizer import BaseTokenizer

__all__ = ['AnalyzedField']

class AnalyzedField(models.Field):
    def __init__(self, *args, **kwargs):
        super(AnalyzedField, self).__init__(*args, **kwargs)
        as_textfield = kwargs.pop('as_textfield', False)
        self._tokenizer = kwargs.pop("tokenizer", BaseTokenizer)()
        self.parent_field = models.CharField(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(AnalyzedField, self).contribute_to_class(cls, "%s_analyzed" % name)
        setattr(self, 'parent_field_name', name)
        cls.add_to_class(name, self.parent_field)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if lookup_type == 'exact':
            return { "$all" : self._tokenizer.tokenize(value)}
        else:
            raise TypeError('Lookup type %r not supported for fulltext queries.' % lookup_type)

    def pre_save(self, model_instance, add):
        return self._tokenizer.tokenize(getattr(model_instance, self.parent_field_name))
