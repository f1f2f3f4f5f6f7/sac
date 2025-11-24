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
def actualizar_imagen_item(request):
    """
    Actualiza o sube la imagen de un item específico del inventario.
    Recibe: inventario_numero y archivo de imagen
    """
    inventario_numero = request.data.get('inventario')
    archivo_imagen = request.FILES.get('imagen')
    
    # Validaciones
    if not inventario_numero:
        return Response(
            {"error": "Debes enviar el número de inventario en el campo 'inventario'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    if not archivo_imagen:
        return Response(
            {"error": "Debes enviar un archivo de imagen en el campo 'imagen'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Validar que es una imagen
    if not archivo_imagen.content_type.startswith('image/'):
        return Response(
            {"error": "El archivo debe ser una imagen."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        with connection.cursor() as cursor:
            # Verificar que el item existe y pertenece al usuario autenticado
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
            
            # Verificar que el usuario autenticado es el responsable del item
            if recibido_por_id != request.user_id:
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [recibido_por_id])
                responsable = cursor.fetchone()
                nombre_responsable = responsable[0] if responsable else "Usuario desconocido"
                
                return Response(
                    {"error": f"No tienes permisos para actualizar este item. Responsable: {nombre_responsable}."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            # Generar nombre único con extensión webp
            filename = f"inventario_{inventario_numero}_{uuid.uuid4().hex[:8]}.webp"

            # Crear directorio si no existe
            images_dir = settings.MEDIA_ROOT / 'inventario_images'
            os.makedirs(images_dir, exist_ok=True)

            # Ruta completa del archivo
            file_path = images_dir / filename

            # Procesar y convertir a WebP
            try:
                with Image.open(archivo_imagen) as original_image:
                    
                    # Aplicar corrección de orientación EXIF si existe
                    original_image = ImageOps.exif_transpose(original_image)
                    
                    # Convertir a RGB si tiene canal alpha
                    if original_image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', original_image.size, (255, 255, 255))
                        mask = original_image.split()[-1] if original_image.mode in ('RGBA', 'LA') else None
                        background.paste(original_image, mask=mask)
                        cleaned_image = background
                    elif original_image.mode == 'P':
                        cleaned_image = original_image.convert('RGB')
                    else:
                        cleaned_image = original_image.convert('RGB')
                    
                    # Redimensionar si es muy grande
                    if cleaned_image.width > 1920 or cleaned_image.height > 1080:
                        cleaned_image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    
                    # Eliminar metadatos recreando la imagen
                    data = list(cleaned_image.getdata())
                    new_image = Image.new(cleaned_image.mode, cleaned_image.size)
                    new_image.putdata(data)
                    
                    # Guardar en formato WebP SIN METADATOS
                    new_image.save(file_path, 'WEBP', quality=85, method=6, save_all=False)
                    
            except Exception as resize_error:
                print(f"Error procesando imagen: {resize_error}")
                return Response(
                    {"error": f"Error al procesar la imagen: {str(resize_error)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Ruta relativa para la base de datos
            foto_nueva = f"inventario_images/{filename}"
            
            # Actualizar la base de datos
            cursor.execute("""
                UPDATE inventario_items 
                SET foto = %s 
                WHERE inventario = %s
            """, [foto_nueva, inventario_numero])
            
            # Si había una imagen anterior, opcionalmente borrarla
            if foto_anterior:
                foto_anterior_path = settings.MEDIA_ROOT / foto_anterior
                if foto_anterior_path.exists():
                    try:
                        os.remove(foto_anterior_path)
                    except Exception as e:
                        print(f"Error borrando imagen antigua: {e}")
            
            return Response(
                {
                    "status": "ok",
                    "mensaje": "Imagen actualizada correctamente",
                    "inventario": inventario_numero,
                    "imagen_url": f"{settings.MEDIA_URL}{foto_nueva}"
                },
                status=status.HTTP_200_OK,
            )
    
    except Exception as e:
        return Response(
            {"error": f"Error al actualizar imagen: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )