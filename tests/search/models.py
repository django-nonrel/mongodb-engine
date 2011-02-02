from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django_mongodb_engine.fields import AnalyzedField

class Blog(models.Model):
    content = AnalyzedField(max_length=255)

    def __unicode__(self):
        return "Blog"
