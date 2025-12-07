from django.urls import path
from .views import actualizar_info_item

urlpatterns = [
    path("actualizar-item/", actualizar_info_item, name="actualizar_info_item"),
]



