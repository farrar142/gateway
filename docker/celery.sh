mkdir logs
celery -A base worker --beat --scheduler django --max-tasks-per-child=1 --autoscale=4,1 --loglevel=info --logfile=/usr/src/app/logs/$1_celerybeat.log -E -n master@node