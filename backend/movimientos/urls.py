from django.urls import path
from .views import solicitud_prestamo, solicitud_baja, solicitud_traslado

urlpatterns = [
    # Endpoints para crear movimientos
    path("registrar_prestamo/", solicitud_prestamo, name="registrar_prestamo"),
    path("solicitud_baja/", solicitud_baja, name="solicitud_baja"),
    path("solicitud_traslado/", solicitud_traslado, name="solicitud_traslado"),
    
]
