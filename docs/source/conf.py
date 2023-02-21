# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))
from novalabs.utils import *

# -- Project information

project = 'NovaLabs backtest'
copyright = '2022, NovaLabs'
author = 'NovaLabs'

release = ''
version = '1.1.4'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
]

napoleon_google_docstring = True
napoleon_use_param = False
napoleon_use_ivar = True

intersphinx_mapping = {
    'python': ('https://docs.python.org/3.9/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'
