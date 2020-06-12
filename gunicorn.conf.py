import multiprocessing
from project.settings import DEBUG

bind = "127.0.0.1:8000" if DEBUG else "unix:sub.socket"
pidfile = "sub.pid"
workers = 1 if DEBUG else multiprocessing.cpu_count() * 2 + 1
threads = 1 if not DEBUG else multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread" if DEBUG else "meinheld.gmeinheld.MeinheldWorker"
reload = DEBUG
