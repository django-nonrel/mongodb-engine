from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    
    def __unicode__(self):
        return "Post: %s" % self.title

class Record(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    
    def __unicode__(self):
        return "Record: %s" % self.title
    