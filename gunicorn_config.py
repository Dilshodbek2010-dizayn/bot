import os

# Bind to PORT provided by Render
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker configuration
workers = 1
worker_class = "sync"
threads = 2

# Timeout settings
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload app
preload_app = True