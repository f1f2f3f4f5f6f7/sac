from django.urls import path
from .views import actualizar_imagen_item

urlpatterns = [
    path("actualizar-imagen/", actualizar_imagen_item, name="actualizar_imagen_item"),
]



