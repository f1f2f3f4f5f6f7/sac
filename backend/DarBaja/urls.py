# inventario/urls.py
from django.urls import path
from .views import solicitud_baja

urlpatterns = [
    path("solicitud-baja/", solicitud_baja, name="solicitud_baja"),
]
