cd /srv/django/gfm && \
source .venv/bin/activate && \
git fetch origin && git checkout main && git pull && \
pip install -r requirements.txt && \
python manage.py migrate --settings=config.settings.prod && \
python manage.py collectstatic --noinput --settings=config.settings.prod && \
sudo systemctl restart django-gunicorn && \
curl -I http://127.0.0.1:8001/gfm/

# logs
#sudo journalctl -u django-gunicorn -n 80 --no-pager