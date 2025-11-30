from django.urls import path
from .views import buscar_inventario

urlpatterns = [
    path("buscar/", buscar_inventario, name="buscar_inventario"),
]