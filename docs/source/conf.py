# coding: utf-8
import django_mongodb_engine

project = u'Django MongoDB Engine'
copyright = u'2011, Jonas Haag, Flavio Percoco Premoli, Alberto Paro and contributors'
version = release = ''.join(map(str, django_mongodb_engine.__version__))


extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo',
              'sphinx.ext.coverage']

master_doc = 'index'
source_suffix = '.rst'
exclude_patterns = ['_build']

add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

pygments_style = 'friendly'

intersphinx_mapping = {
    'python' : ('http://docs.python.org', None),
    'pymongo': ('http://api.mongodb.org/python/current/', None),
    'django' : ('http://docs.djangoproject.com/en/dev/',
                'http://docs.djangoproject.com/en/dev/_objects/')
}

# -- Options for HTML output ---------------------------------------------------

html_theme = 'mongodbtheme'
#html_theme_options = {}
html_theme_path = ['mongodbtheme', '.']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Django MongoDB Engine'

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'**' : ['localtoc.html', 'sidebar.html']}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False
