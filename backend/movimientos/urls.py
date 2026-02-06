from django.urls import path
from .views import (
    solicitud_prestamo,
    solicitud_baja,
    solicitud_traslado,
    historial_trazabilidad,
    consultar_trazabilidad_usuario, 
    trazabilidad_por_elemento,
    confirmar_o_cancelar_baja,
    confirmar_cancelar_prestamo,
    confirmar_cancelar_traslado,
    listar_notificaciones,
    descargar_archivo_trazabilidad,
)

urlpatterns = [
    # Endpoints para crear movimientos
    path("registrar_prestamo/", solicitud_prestamo, name="registrar_prestamo"),
    path("solicitud_baja/", solicitud_baja, name="solicitud_baja"),
    path("solicitud_traslado/", solicitud_traslado, name="solicitud_traslado"),
    path("consultar_trazabilidad/", historial_trazabilidad, name="consultar_trazabilidad"),
    path("consultar_trazabilidad_usuario/", consultar_trazabilidad_usuario, name="consultar_trazabilidad_usuario",),
    path("consultar_trazabilidad_elemento/", trazabilidad_por_elemento, name="consultar_trazabilidad_elemento",),
    path("confirmar_cancelar_baja/", confirmar_o_cancelar_baja, name = "confirmar_cancelar_baja"),
    path("confirmar_cancelar_prestamo/", confirmar_cancelar_prestamo, name = "confirmar_cancelar_prestamo"),
    path("confirmar_cancelar_traslado/", confirmar_cancelar_traslado, name = "confirmar_cancelar_traslado"),
    path("listar_notificaciones/", listar_notificaciones, name = "listar_notificaciones"),
    path("descargar_archivo_trazabilidad/", descargar_archivo_trazabilidad, name = "descargar_archivo_trazabilidad"),


]