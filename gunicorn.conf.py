import multiprocessing
from project.settings import DEBUG

bind = "unix:dub.socket" if not DEBUG else "127.0.0.1:8000"
pidfile = "dub.pid"
workers = multiprocessing.cpu_count() * 2 + 1 if not DEBUG else 1
worker_class = "meinheld.gmeinheld.MeinheldWorker"
reload = DEBUG
