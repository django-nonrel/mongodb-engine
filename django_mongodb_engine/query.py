from djangotoolbox.fields import ListField, SetField, DictField

__all__ = ['BaseExtraQuery', 'A']

class BaseExtraQuery(object):
    
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("")
        
    def as_q(self, model, field):
        raise NotImplementedError("")
        
class A(BaseExtraQuery):

    def __init__(self, op, value):
        self.op = op
        self.val = value

    def as_q(self, model, field):
        if isinstance(field, (DictField, ListField, SetField)):
            return "%s.%s" % (field.name, self.op), self.val