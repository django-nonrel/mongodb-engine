from django_mongodb_engine.query import BaseExtraQuery

class Ft(BaseExtraQuery):
    
    def __init__(self, query):
        self.value = query
        
    def as_q(self, model, field):
        tokens = self.model._meta.tokenizer.tokenize(self.value)
        return "_%s_ft" % field.name, tokens