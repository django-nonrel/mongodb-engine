# coding: utf-8
import sys; sys.path.append('.')
from .utils import get_current_year, get_git_head

project = 'Django MongoDB Engine'
copyright = '2010-%d, Jonas Haag, Flavio Percoco Premoli and contributors' % \
            get_current_year()

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

master_doc = 'index'
exclude_patterns = ['_build']

pygments_style = 'friendly'

intersphinx_mapping = {
    'python':  ('http://docs.python.org', None),
    'pymongo': ('http://api.mongodb.org/python/current/', None),
    'django':  ('http://docs.djangoproject.com/en/dev/',
                'http://docs.djangoproject.com/en/dev/_objects/'),
}

# -- Options for HTML output ---------------------------------------------------

html_title = project

html_last_updated_fmt = '%b %d, %Y'
git_head = get_git_head()
if git_head:
    html_last_updated_fmt += ' (%s)' % git_head[:7]

html_theme = 'mongodbtheme'
html_theme_path = ['mongodbtheme', '.']
html_show_copyright = False

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'**': ['localtoc.html', 'sidebar.html']}

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False
