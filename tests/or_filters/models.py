from django.db import models

class Simple(models.Model):
    a = models.IntegerField()
    b = models.IntegerField(null=True)

    def __repr__(self):
        return '<Simple a=%d b=%d>' % (self.a, self.b)
