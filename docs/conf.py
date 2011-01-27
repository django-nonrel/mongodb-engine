# -*- coding: utf-8 -*-

import sys
import os

this = os.path.dirname(os.path.abspath(__file__))

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.join(os.pardir, "tests"))
sys.path.append(os.path.join(this, "_ext"))
import django_mongodb_engine

# General configuration
# ---------------------

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              #'sphinxcontrib.issuetracker',
              'sphinx.ext.todo',
              'sphinx.ext.intersphinx',
              'django_mongodb_engine_docs',
              ]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-mongodb-engine'
copyright = u'2009-2010: Flavio Percoco, Alberto Paro, Jonas Haag & contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, django_mongodb_engine.__version__[0:2]))
# The full version, including alpha/beta/rc tags.
release = '.'.join(map(str, django_mongodb_engine.__version__))

exclude_trees = ['.build']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

latex_documents = [
  ('index', 'django_mongodb_engine.tex', ur'django-mongodb-engine Documentation',
   ur'Flavio Percoco, Alberto Paro, Jonas Haag', 'manual'),
]

html_theme = 'nature'
html_theme_options = {'nosidebar' : 'true'}
# html_theme_path = ["_theme"]
# html_sidebars = {
#     'index': ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
#     '**': ['sidebarlogo.html', 'relations.html',
#            'sourcelink.html', 'searchbox.html'],
# }

### Issuetracker

issuetracker = "github"
issuetracker_user = "django-mongodb-engine"
issuetracker_project = "mongodb-engine"
issuetracker_issue_pattern = r'[Ii]ssue #(\d+)'

intersphinx_mapping = {'python' : ('http://docs.python.org', None),
                       'django' : ('http://docs.djangoproject.com/en/dev/_objects/', None)}
