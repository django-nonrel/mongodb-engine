
from djangotoolbox.fields import AbstractIterableField

class A(object):
    
    def __init__(self, op, value):
        self.op = op
        self.val = value
        
    def as_q(self, field):
        if isinstance(field, (AbstractIterableField)):
            return "%s.%s" % (field.name, self.op), self.val