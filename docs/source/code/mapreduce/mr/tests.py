mapfunc = """
function() {
  this.text.split(' ').forEach(
    function(word) { emit(word, 1) }
  )
}
"""

reducefunc = """
function reduce(key, values) {
  return values.length; /* == sum(values) */
}
"""

__test__ = {
    'mr': """
>>> from models import Author, Article

>>> bob = Author.objects.create()
>>> ann = Author.objects.create()

>>> bobs_article = Article.objects.create(author=bob, text="A B C")
>>> anns_article = Article.objects.create(author=ann, text="A B C D E")

Map/Reduce over all articles:
>>> for pair in Article.objects.map_reduce(mapfunc, reducefunc, 'wordcount'):
...     print pair.key, pair.value
A 2.0
B 2.0
C 2.0
D 1.0
E 1.0

Map/Reduce over Bob's articles:
>>> for pair in Article.objects.filter(author=bob).map_reduce(
            mapfunc, reducefunc, 'wordcount'):
...    print pair.key, pair.value
A 1.0
B 1.0
C 1.0
"""}
