__test__ = {
    'v4': """
>>> from nonrelblog.models import Post
>>> from nonrelblog.models import Comment, Author
>>> Comment(
...     author=Author(name='Bob', email='bob@example.org'),
...     text='The cake is a lie'
... ).save()
>>> comment = Comment.objects.get()
>>> comment.author
<Author: Bob (bob@example.org)>
>>> Post(
...     title='I like cake',
...     comments=[comment]
... ).save()
>>> post = Post.objects.get(title='I like cake')
>>> post.comments
[<Comment: Comment object>]
>>> post.comments[0].author.email
u'bob@example.org'
"""}
