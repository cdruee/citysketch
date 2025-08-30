# Configuration file for the Sphinx documentation builder.
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'CitySketch'
copyright = '2025, Clemens Drüe'
author = 'Clemens Drüe'
version = '1.0'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.imgmath',
    'sphinx_rtd_theme',
]


templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = '_static/citysketch_logo.png'

latex_engine = 'pdflatex'
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
}

latex_documents = [
    ('index', 'citysketch-manual.tex', 'CitySketch User Manual',
     'Clemens Drüe', 'manual'),
]

todo_include_todos = True

def setup(app):
    app.add_css_file('custom.css')
