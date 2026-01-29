from django.urls import path
from .views import buscar_inventario, listar_edificios, listar_escuelas

urlpatterns = [
    path("buscar/", buscar_inventario, name="buscar_inventario"),
    path("listar-edificios/", listar_edificios, name="listar_edificios"),
    path("listar-escuelas/", listar_escuelas, name="listar_escuelas"),
]   