from django.db.models import Aggregate

class MongoAggregate(Aggregate):
    is_ordinal = False
    is_computed = False
    
    def add_to_query(self, query, alias, col, source, is_summary):
        """Add the aggregate to the nominated query.

        This method is used to convert the generic Aggregate definition into a
        backend-specific definition.

         * query is the backend-specific query instance to which the aggregate
           is to be added.
         * col is a column reference describing the subject field
           of the aggregate. It can be an alias, or a tuple describing
           a table and column name.
         * source is the underlying field or aggregate definition for
           the column reference. If the aggregate is not an ordinal or
           computed type, this reference is used to determine the coerced
           output type of the aggregate.
         * is_summary is a boolean that is set True if the aggregate is a
           summary value rather than an annotation.
        """
        self.alias = alias
        self.field = self.source = source
        
        if self.valid_field_types and not self.source.get_internal_type() in self.valid_field_types:
            raise RuntimeError()
        query.aggregates[alias] = self

    def as_sql(self):
        pass

class Count(MongoAggregate):
    name = "Count"
    valid_field_types = None
    
    def as_query(self, query):
        return {self.alias : 0}, \
               "out.%s++" % (self.alias), \
               ""
  
class Min(MongoAggregate):
    name = "Min"
    valid_field_types = ("IntegerField", "FloatField", 'DateField', 'DateTimeField', 'TimeField')
    
    def as_query(self, query):
        return {self.alias : "null"}, \
               "out.%s = (out.%s == 'null' || doc.%s < out.%s) ? doc.%s: out.%s" % (self.alias, self.alias, self.lookup, self.alias, self.lookup, self.alias), \
               ""
        
class Max(MongoAggregate):
    name = "Max"
    valid_field_types = ("IntegerField", "FloatField", 'DateField', 'DateTimeField', 'TimeField')
    
    def as_query(self, query):
        return {self.alias : "null"}, \
               "out.%s = (out.%s == 'null' || doc.%s > out.%s) ? doc.%s: out.%s" % (self.alias, self.alias, self.lookup, self.alias, self.lookup, self.alias), \
               ""

class Avg(MongoAggregate):
    name = "Avg"
    is_computed = True
    valid_field_types = ("IntegerField", "FloatField")
    
    def as_query(self, query):
        return {"%s__count" % self.alias : 0, "%s__total" % self.alias : 0}, \
                "out.%s__count++; out.%s__total+=doc.%s" % (self.alias, self.alias, self.lookup), \
                "out.%s = out.%s__total / out.%s__count" % (self.alias, self.alias, self.alias)