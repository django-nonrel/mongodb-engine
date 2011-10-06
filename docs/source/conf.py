# coding: utf-8
import django_mongodb_engine

project = 'Django MongoDB Engine'
copyright = '2011, Jonas Haag, Flavio Percoco Premoli and contributors'
version = release = ''.join(map(str, django_mongodb_engine.__version__))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo',
              'sphinx.ext.coverage']

master_doc = 'index'
exclude_patterns = ['_build']

pygments_style = 'friendly'

intersphinx_mapping = {
    'python' : ('http://docs.python.org', None),
    'pymongo': ('http://api.mongodb.org/python/current/', None),
    'django' : ('http://docs.djangoproject.com/en/dev/',
                'http://docs.djangoproject.com/en/dev/_objects/')
}

# -- Options for HTML output ---------------------------------------------------

from subprocess import check_output, CalledProcessError
GIT_HEAD = None
try:
    GIT_HEAD = check_output(['git', 'rev-parse', 'HEAD'])
except CalledProcessError:
    pass
except OSError, exc:
    if exc.errno != 2:
        raise


html_title = project
html_last_updated_fmt = '%b %d, %Y'
if GIT_HEAD:
    html_last_updated_fmt += ' (%s)' % GIT_HEAD[:7]
html_show_copyright = False
html_theme = 'mongodbtheme'
html_theme_path = ['mongodbtheme', '.']

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'**' : 'sidebar-contribute.html'}

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False
