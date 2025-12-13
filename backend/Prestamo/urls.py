from django.urls import path
from .views import solicitud_prestamo

urlpatterns = [
    path("registrar_prestamo/", solicitud_prestamo, name="registrar_prestamo"),
]