from multiprocessing import cpu_count

from project.settings import DEBUG

bind = "127.0.0.1:8000" if DEBUG else "unix:sub.socket"
pidfile = "sub.pid"
threads = 1 if DEBUG else cpu_count() * 2 + 1
worker_class = "gthread"
reload = DEBUG
