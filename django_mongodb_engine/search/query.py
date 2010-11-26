from django_mongodb_engine.query import BaseExtraQuery

class Ft(BaseExtraQuery):
    """
    FullText query.
    
    Should we use this or __ft ?
    """
    
    def __init__(self, query):
        self.value = query
        
    def as_q(self, model, field):
        tokens = self.model._meta.tokenizer.tokenize(self.value)
        return "_%s_ft" % field.name, tokens