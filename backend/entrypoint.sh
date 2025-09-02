#!/bin/sh

echo "Esperando a que la base de datos esté lista..."
# Espera hasta que la DB esté disponible (opcional)
sleep 5

echo "Ejecutando migraciones..."
python manage.py makemigrations
python manage.py migrate

echo "Iniciando el servidor Django..."
python manage.py runserver 0.0.0.0:8000
