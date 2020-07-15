from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader
from num2words import num2words

from app.filters import age, country, parser, shortdate, superscript
from project.settings import DEBUG

env = Environment()
env.bytecode_cache = FileSystemBytecodeCache()
env.loader = FileSystemLoader('templates')
env.auto_reload = DEBUG

env.filters['age'] = age
env.filters['country'] = country
env.filters['num2words'] = num2words
env.filters['parser'] = parser
env.filters['shortdate'] = shortdate
env.filters['superscript'] = superscript

env.globals['brand'] = "Subreply"
env.globals['v'] = 12
