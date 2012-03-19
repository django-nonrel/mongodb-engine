class MongoAggregate(object):
    is_ordinal = False
    is_computed = False
    reduce_template = NotImplemented
    finalize_template = ''

    def __init__(self, alias, lookup, source):
        self.alias = alias
        self.lookup = lookup
        self.field = self.source = source

    def format(self, template):
        alias = 'out.%s' % self.alias
        lookup = 'doc.%s' % self.lookup
        return template.format(alias=alias, lookup=lookup)

    def initial(self):
        return {self.alias: self.initial_value}

    def reduce(self):
        return self.format(self.reduce_template)

    def finalize(self):
        return self.format(self.finalize_template)

    def as_sql(self):
        raise NotImplementedError


class Count(MongoAggregate):
    is_ordinal = True
    initial_value = 0
    reduce_template = '{alias}++'


class Min(MongoAggregate):
    initial_value = float('inf')
    reduce_template = '{alias} = ({lookup} < {alias}) ? {lookup}: {alias}'


class Max(MongoAggregate):
    initial_value = float('-inf')
    reduce_template = '{alias} = ({lookup} > {alias}) ? {lookup}: {alias}'


class Avg(MongoAggregate):
    is_computed = True

    def initial(self):
        return {'%s__count' % self.alias: 0, '%s__total' % self.alias: 0}

    reduce_template = '{alias}__count++; {alias}__total += {lookup}'
    finalize_template = '{alias} = {alias}__total / {alias}__count'


class Sum(MongoAggregate):
    is_computed = True
    initial_value = 0

    reduce_template = '{alias} += {lookup}'


_AGGREGATION_CLASSES = dict((cls.__name__, cls)
                            for cls in MongoAggregate.__subclasses__())

def get_aggregation_class_by_name(name):
    return _AGGREGATION_CLASSES[name]
