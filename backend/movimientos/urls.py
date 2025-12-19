from django.urls import path
from .views import solicitud_prestamo, solicitud_baja

urlpatterns = [
    # Endpoints para crear movimientos
    path("registrar_prestamo/", solicitud_prestamo, name="registrar_prestamo"),
    path("solicitud-baja/", solicitud_baja, name="solicitud_baja"),
    

]
