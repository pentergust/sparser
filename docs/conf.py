"""Configuration file for the Sphinx documentation builder."""

project = 'SPlatform'
author = 'Milinuri Nirvalen'
copyright = f'2024, {author}'
release = '6.1'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.todo',
    'sphinx.ext.autodoc',  # Core library for html generation from docstrings
    'sphinx.ext.autosummary',  # Create neat summary tables
    'sphinx_copybutton'
]

todo_include_todos = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'ru'


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_book_theme'
html_logo = "_images/sp_ava.png"
html_static_path = ['_static']
highlight_language = "python3"
