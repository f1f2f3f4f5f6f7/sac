from django.urls import path
from . import views

urlpatterns = [
    # Endpoints para crear movimientos
    path('prestamos/', views.crear_prestamo, name='crear_prestamo'),
    path('traslados/', views.crear_traslado, name='crear_traslado'),
    path('bajas/', views.dar_baja_activo, name='dar_baja_activo'),
    path('devoluciones/', views.devolver_prestamo, name='devolver_prestamo'),
    
    # Endpoints para consultar información
    path('trazabilidad/<int:inventario_id>/', views.obtener_trazabilidad_inventario, name='trazabilidad_inventario'),
    path('mis-movimientos/', views.obtener_movimientos_usuario, name='mis_movimientos')
]
