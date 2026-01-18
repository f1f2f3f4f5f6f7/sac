from django.urls import path
from .views import (
    solicitud_prestamo,
    solicitud_baja,
    solicitud_traslado,
    historial_trazabilidad,
    consultar_trazabilidad_usuario, 
    trazabilidad_por_elemento,
)

urlpatterns = [
    # Endpoints para crear movimientos
    path("registrar_prestamo/", solicitud_prestamo, name="registrar_prestamo"),
    path("solicitud_baja/", solicitud_baja, name="solicitud_baja"),
    path("solicitud_traslado/", solicitud_traslado, name="solicitud_traslado"),
    path("consultar_trazabilidad/", historial_trazabilidad, name="consultar_trazabilidad"),
    path("consultar_trazabilidad_usuario/", consultar_trazabilidad_usuario, name="consultar_trazabilidad_usuario",),
    path("consultar_trazabilidad_elemento/", trazabilidad_por_elemento, name="consultar_trazabilidad_elemento",),

]