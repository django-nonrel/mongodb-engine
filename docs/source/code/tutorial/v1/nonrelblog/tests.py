__test__ = {'v1': """
>>> from nonrelblog.models import Post
>>> post = Post.objects.create(
...     title='Hello MongoDB!',
...     text='Just wanted to drop a note from Django. Cya!',
...     tags=['mongodb', 'django']
... )

Surely we want to add some comments.

>>> post.comments
[]
>>> post.comments.extend(['Great post!', 'Please, do more of these!'])
>>> post.save()

Look and see, it has actually been saved!

>>> Post.objects.get().comments
[u'Great post!', u'Please, do more of these!']
"""}
