from urllib.parse import quote_plus

from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader
from emoji import emojize

from app.filters import age, city, fibojize, parser, shortdate, superscript
from project.settings import DEBUG, FERNET

env = Environment(autoescape=True)

env.auto_reload = DEBUG
env.bytecode_cache = FileSystemBytecodeCache()
env.loader = FileSystemLoader('templates')

env.filters['age'] = age
env.filters['city'] = city
env.filters['decode'] = lambda m: FERNET.decrypt(m.encode()).decode()
env.filters['emojize'] = emojize
env.filters['fibojize'] = fibojize
env.filters['parser'] = parser
env.filters['quote'] = quote_plus
env.filters['shortdate'] = shortdate
env.filters['superscript'] = superscript

env.globals['brand'] = "Subreply"
env.globals['v'] = 184


def render(page, **kwargs):
    print('\n---', page, kwargs.get('view', ''))
    template = env.get_template(f'pages/{page}.html')
    return template.render(**kwargs)
