echo yes | python3 manage.py collectstatic --settings=base.settings.prod
python3 manage.py migrate --settings=base.settings.prod
# uwsgi --env DJANGO_SETTINGS_MODULE=base.settings.prod --ini base.local.ini
rm -rf /usr/src/app/socket/uvicorn.sock
uvicorn base.asgi:application --port 8000 --host 0.0.0.0 --workers $(($(awk '/^processor/{n+=1}END{print n}' /proc/cpuinfo)*$1+1)) --lifespan off --uds /usr/src/app/socket/uvicorn.sock --log-config log.ini