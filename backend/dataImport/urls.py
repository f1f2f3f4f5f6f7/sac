from django.urls import path
from .views import importar_inventario

urlpatterns = [
    path("importar-inventario/", importar_inventario, name="importar_inventario"),
]
