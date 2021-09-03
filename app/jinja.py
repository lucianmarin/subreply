from urllib.parse import quote_plus

from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader
from num2words import num2words
from emoji import emojize

from app.filters import age, city, parser, shortdate, superscript
from project.settings import DEBUG

env = Environment()
env.bytecode_cache = FileSystemBytecodeCache()
env.loader = FileSystemLoader('templates')
env.auto_reload = DEBUG

env.filters['age'] = age
env.filters['city'] = city
env.filters['emojize'] = emojize
env.filters['num2words'] = num2words
env.filters['parser'] = parser
env.filters['quote'] = quote_plus
env.filters['shortdate'] = shortdate
env.filters['superscript'] = superscript

env.globals['brand'] = "Subreply"
env.globals['v'] = 1


def render(page, **kwargs):
    print('-----', page, kwargs.get('view', ''))
    template = env.get_template(f'pages/{page}.html')
    return template.render(**kwargs)
