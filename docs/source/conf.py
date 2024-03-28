# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import sphinx_bootstrap_theme

sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))

os.environ['PYPLATE_CONFIG'] = os.path.abspath(os.path.join('..', '..'))
# -- Project information -----------------------------------------------------

project = 'PyPlate'
copyright = '2024, Eugene Kwan and James Marvin'
author = 'Eugene Kwan and James Marvin'

# The full version, including alpha/beta/rc tags
release = '0.1'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "m2r2",
]

source_suffix = ['.rst', '.md']

math_output = 'MathML'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

autosummary_generate = True
autodoc_default_options = {'members': True, 'undoc-members': True, 'show-inheritance': True, 'inherited-members': True}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'bootstrap'
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

html_theme_options = {
    'navbar_title': "PyPlate",
    'navbar_site_name': "Contents",
    'navbar_links': [
        ("README", "index"),
        ("Users Guide", "users_guide"),
        ("Reference Guide", "api"),
        ("API", "pyplate"),
        ("Extra Docs", "extras"),
        ("GitHub", "https://github.com/ekwan/PyPlate", True),
    ],
    'bootswatch_theme': "cerulean",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
