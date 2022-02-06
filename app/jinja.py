from urllib.parse import quote_plus

from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader
from emoji import emojize

from app.filters import age, city, parser, shortdate, superscript
from project.settings import DEBUG

env = Environment(autoescape=True)

env.auto_reload = DEBUG
env.bytecode_cache = FileSystemBytecodeCache()
env.loader = FileSystemLoader('templates')

env.filters['age'] = age
env.filters['city'] = city
env.filters['emojize'] = emojize
env.filters['parser'] = parser
env.filters['quote'] = quote_plus
env.filters['shortdate'] = shortdate
env.filters['superscript'] = superscript

env.globals['brand'] = "Subreply"
env.globals['v'] = 157


def render(page, **kwargs):
    print('\n---', page, kwargs.get('view', ''))
    template = env.get_template(f'pages/{page}.html')
    return template.render(**kwargs)
