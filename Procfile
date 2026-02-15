web: cd backend && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120 --access-logfile - --error-logfile -
worker: cd backend && celery -A tasks.celery_app worker --loglevel=info --concurrency=4
beat: cd backend && celery -A tasks.celery_app beat --loglevel=info
