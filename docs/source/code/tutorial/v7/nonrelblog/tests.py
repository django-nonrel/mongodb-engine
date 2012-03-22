mapfunc = """
function map() {
  /* `this` refers to the current document */
  this.comments.forEach(function(comment) {
    emit(comment.author.name, 1);
  });
}
"""

reducefunc = """
function reduce(id, values) {
  /* [1, 1, ..., 1].length is the same as sum([1, 1, ..., 1]) */
  return values.length;
}
"""

__test__ = {'mapreduce': """
>>> from nonrelblog.models import *

Add some data so we can actually mapreduce anything.
Bob:   3 comments
Ann:   6 comments
Alice: 9 comments
>>> authors = [Author(name='Bob', email='bob@example.org'),
...            Author(name='Ann', email='ann@example.org'),
...            Author(name='Alice', email='alice@example.org')]
>>> for distribution in [(0, 1, 2), (1, 2, 3), (2, 3, 4)]:
...     comments = []
...     for author, ncomments in zip(authors, distribution):
...         comments.extend([Comment(author=author)
...                         for i in xrange(ncomments)])
...     Post(comments=comments).save()

------------------------
Kick off the Map/Reduce:
------------------------
>>> pairs = Post.objects.map_reduce(mapfunc, reducefunc, out='temp',
...                                 delete_collection=True)
>>> for pair in pairs:
...     print pair.key, pair.value
Alice 9.0
Ann 6.0
Bob 3.0
"""}
