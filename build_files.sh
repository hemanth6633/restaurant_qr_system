#!/bin/bash
echo "Building the project..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Make migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Collect Static..."
python manage.py collectstatic --noinput --clear
