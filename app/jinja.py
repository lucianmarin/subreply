from datetime import datetime
from textwrap import shorten
from urllib.parse import quote_plus

from emoji import emojize
from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader

from app.filters import age, city, fibojize, parser, shortdate
from project.settings import DEBUG

env = Environment(autoescape=True)

env.auto_reload = DEBUG
env.bytecode_cache = FileSystemBytecodeCache()
env.loader = FileSystemLoader('templates')

env.filters['age'] = age
env.filters['city'] = city
env.filters['emojize'] = emojize
env.filters['fibojize'] = fibojize
env.filters['parser'] = parser
env.filters['quote'] = quote_plus
env.filters['shortdate'] = shortdate
env.filters['isoformat'] = lambda ts: datetime.fromtimestamp(ts).isoformat()
env.filters['shorten'] = lambda text, width: shorten(text, width, placeholder="...")
env.filters['keywords'] = lambda e: ", ".join(e[1:-1].split("_"))

env.globals['brand'] = "Subreply"
env.globals['v'] = 191


def render(page, **kwargs):
    print('\n---', page, kwargs.get('view', ''))
    template = env.get_template(f'pages/{page}.html')
    return template.render(**kwargs)
