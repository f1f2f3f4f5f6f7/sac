from django.shortcuts import render

import io
import json
import pandas as pd
import datetime
import unicodedata
import re
import os
import uuid
from PIL import Image, ImageOps
from openpyxl import load_workbook
from django.conf import settings
from rapidfuzz import fuzz
from django.db import connection, transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from accounts.views import login_required_api  # Importar el decorador de autenticación
from psycopg2.extras import execute_values




@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@login_required_api
def actualizar_info_item(request):
    """
    Actualiza la imagen y/o los campos extra de un item específico del inventario.
    Campos permitidos:
        - inventario (obligatorio)
        - imagen (opcional)
        - ubicacion_id (opcional)
        - salon (opcional)
        - observaciones (opcional)
    """

    inventario_numero = request.data.get('inventario')
    archivo_imagen = request.FILES.get('imagen')

    # Nuevos campos opcionales
    ubicacion_id = request.data.get('ubicacion_id')
    salon = request.data.get('salon')
    observaciones = request.data.get('observaciones')
    inventoried = request.data.get('inventoried')


    # Validación mínima
    if not inventario_numero:
        return Response(
            {"error": "Debes enviar el número de inventario en el campo 'inventario'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with connection.cursor() as cursor:
            # Verificar existencia
            cursor.execute("""
                SELECT id, foto, recibido_por_id 
                FROM inventario_items 
                WHERE inventario = %s
            """, [inventario_numero])

            item = cursor.fetchone()

            if not item:
                return Response(
                    {"error": f"No se encontró un item con número de inventario '{inventario_numero}'."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            item_id, foto_anterior, recibido_por_id = item

            # Validar permisos
            if recibido_por_id != request.user_id:
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [recibido_por_id])
                responsable = cursor.fetchone()
                nombre_responsable = responsable[0] if responsable else "Usuario desconocido"

                return Response(
                    {"error": f"No tienes permisos para actualizar este item. Responsable: {nombre_responsable}."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # ----------------------------
            # 🔵 1. PROCESAR IMAGEN (solo si viene)
            # ----------------------------
            foto_nueva = None

            if archivo_imagen:
                # Validar tipo
                if not archivo_imagen.content_type.startswith('image/'):
                    return Response(
                        {"error": "El archivo debe ser una imagen."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                filename = f"inventario_{inventario_numero}_{uuid.uuid4().hex[:8]}.webp"

                images_dir = settings.MEDIA_ROOT / 'inventario_images'
                os.makedirs(images_dir, exist_ok=True)

                file_path = images_dir / filename

                try:
                    with Image.open(archivo_imagen) as original_image:

                        original_image = ImageOps.exif_transpose(original_image)

                        if original_image.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', original_image.size, (255, 255, 255))
                            mask = original_image.split()[-1]
                            background.paste(original_image, mask=mask)
                            cleaned_image = background
                        elif original_image.mode == 'P':
                            cleaned_image = original_image.convert('RGB')
                        else:
                            cleaned_image = original_image.convert('RGB')

                        if cleaned_image.width > 1920 or cleaned_image.height > 1080:
                            cleaned_image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)

                        data = list(cleaned_image.getdata())
                        new_image = Image.new(cleaned_image.mode, cleaned_image.size)
                        new_image.putdata(data)

                        new_image.save(file_path, 'WEBP', quality=85, method=6, save_all=False)

                except Exception as resize_error:
                    print(f"Error procesando imagen: {resize_error}")
                    return Response(
                        {"error": f"Error al procesar la imagen: {str(resize_error)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                foto_nueva = f"inventario_images/{filename}"

                # Actualiza solo la foto
                cursor.execute("""
                    UPDATE inventario_items
                    SET foto = %s
                    WHERE inventario = %s
                """, [foto_nueva, inventario_numero])

                # Borrar imagen anterior si existe
                if foto_anterior:
                    foto_anterior_path = settings.MEDIA_ROOT / foto_anterior
                    if foto_anterior_path.exists():
                        try:
                            os.remove(foto_anterior_path)
                        except:
                            pass

            # ----------------------------
            # 🔵 2. ACTUALIZAR CAMPOS EXTRAS
            # ----------------------------

            campos_update = []
            valores = []

            # ubicacion_id (validación básica)
            if ubicacion_id:
                try:
                    int(ubicacion_id)
                except:
                    return Response(
                        {"error": "El valor de 'ubicacion_id' debe ser un número válido."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                campos_update.append("ubicacion_id = %s")
                valores.append(ubicacion_id)

            if salon is not None:
                campos_update.append("salones = %s")
                valores.append(salon)

            if observaciones is not None:
                campos_update.append("observaciones = %s")
                valores.append(observaciones)


            if inventoried is not None:
                valor_bool = str(inventoried).strip().lower()

                if valor_bool in ("true", "1", "yes"):
                    valor_bool = True
                elif valor_bool in ("false", "0", "no"):
                    valor_bool = False
                else:
                    return Response(
                        {"error": "El campo 'inventoried' debe ser true/false o 1/0."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                campos_update.append("inventoried = %s")
                valores.append(valor_bool)

            # Ejecutar update solo si hay campos a actualizar
            if campos_update:
                sql = f"""
                    UPDATE inventario_items
                    SET {', '.join(campos_update)}
                    WHERE inventario = %s
                """
                valores.append(inventario_numero)
                cursor.execute(sql, valores)


            return Response(
                {
                    "status": "ok",
                    "mensaje": "Datos actualizados correctamente",
                    "imagen_actualizada": bool(archivo_imagen),
                    "foto_url": f"{settings.MEDIA_URL}{foto_nueva}" if foto_nueva else None
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        return Response(
            {"error": f"Error al actualizar item: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
