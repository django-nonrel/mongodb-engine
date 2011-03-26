from djangotoolbox.fields import RawField, AbstractIterableField, EmbeddedModelField

DJANGOTOOLBOX_FIELDS = (RawField, AbstractIterableField, EmbeddedModelField)

__all__ = ['A']

class A(object):
    def __init__(self, op, value):
        self.op = op
        self.val = value

    def as_q(self, field):
        if isinstance(field, DJANGOTOOLBOX_FIELDS):
            return "%s.%s" % (field.column, self.op), self.val
        else:
            raise TypeError("Can not use A() queries on %s" % field.__class__.__name__)
