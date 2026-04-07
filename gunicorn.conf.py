# =============================================================================
# Gunicorn configuration
# Docs: https://docs.gunicorn.org/en/stable/settings.html
# =============================================================================

import multiprocessing

# Server socket
bind = "0.0.0.0:8000"

# Workers — formula: (2 × CPU cores) + 1
# Defaulting to 3; override via GUNICORN_WORKERS env var at deploy time
workers = int(__import__('os').environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"

# Timeouts
timeout = 120          # Kill a worker if it doesn't respond within 120s
graceful_timeout = 30  # How long to wait for workers to finish on SIGTERM
keepalive = 5          # Keep idle connections open for 5s

# Logging — send both access and error logs to stdout for Docker log aggregation
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs'

# Process naming
proc_name = "backend-api"

# Reload on code changes (dev only — override with GUNICORN_RELOAD=true)
reload = __import__('os').environ.get('GUNICORN_RELOAD', 'false').lower() == 'true'
