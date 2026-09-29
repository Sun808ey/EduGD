"""Bounded Railway Gunicorn configuration."""

import os


bind = f"0.0.0.0:{int(os.environ.get('PORT', '8000'))}"
workers = 1
threads = 4
timeout = 30
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
access_log_format = "%(m)s %(s)s %(L)s"
