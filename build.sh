
set -o errexit
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
if [{ $CREATE_SUPERUSER }]; then
    python manage.py createsuperuser --noinput --username $SUPERUSER_NAME --email $SUPERUSER_EMAIL
fi