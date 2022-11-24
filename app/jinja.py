from datetime import datetime
from textwrap import shorten
from urllib.parse import quote_plus

from emoji import emojize
from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader

from app.filters import age, parser, timeago
from app.helpers import utc_timestamp
from project.settings import DEBUG

env = Environment(autoescape=True)

env.auto_reload = DEBUG
env.bytecode_cache = FileSystemBytecodeCache()
env.loader = FileSystemLoader('templates')

env.filters['age'] = age
env.filters['city'] = lambda loc: loc.split(",")[0] if "," in loc else loc
env.filters['emojize'] = emojize
env.filters['parser'] = parser
env.filters['quote'] = quote_plus
env.filters['shortdate'] = lambda ts: timeago(utc_timestamp() - ts)
env.filters['isoformat'] = lambda ts: datetime.fromtimestamp(ts).isoformat()
env.filters['shorten'] = lambda txt, w: shorten(txt, w, placeholder="...")
env.filters['keywords'] = lambda emo: ", ".join(emo[1:-1].split("_"))

env.globals['brand'] = "Subreply"
env.globals['v'] = 216


def render(page, **kwargs):
    print('\n---', page, kwargs.get('view', ''))
    template = env.get_template(f'pages/{page}.html')
    return template.render(**kwargs)
