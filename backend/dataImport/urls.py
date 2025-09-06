from django.urls import path
from .views import importar_inventario, obtener_inventario_usuario

urlpatterns = [
    path("importar-inventario/", importar_inventario, name="importar_inventario"),
    path("inventario-usuario/", obtener_inventario_usuario, name="obtener_inventario_usuario"),
]