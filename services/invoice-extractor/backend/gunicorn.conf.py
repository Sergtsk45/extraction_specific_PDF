# gunicorn.conf.py
import os

bind    = f"{os.getenv('FLASK_HOST','0.0.0.0')}:{os.getenv('PORT', os.getenv('FLASK_PORT','5002'))}"
workers = int(os.getenv('GUNICORN_WORKERS', 2))
threads = int(os.getenv('GUNICORN_THREADS', 2))
timeout = int(os.getenv('REQUEST_TIMEOUT_SEC', 120)) + 30
loglevel    = os.getenv('LOG_LEVEL', 'info')
accesslog   = '-'
errorlog    = '-'
worker_class = 'sync'
