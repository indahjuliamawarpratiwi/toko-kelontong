import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = (multiprocessing.cpu_count() * 2) + 1
timeout = 60
accesslog = '-'
errorlog = '-'