web: gunicorn server:app
worker: celery worker --app=server.celery --concurrency 2
