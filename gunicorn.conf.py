from project.settings import DEBUG

bind = "127.0.0.1:8000" if DEBUG else "unix:sub.socket"
pidfile = "sub.pid"
workers = 1 if DEBUG else 3
reload = DEBUG
