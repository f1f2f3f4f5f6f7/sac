from django.db import connection
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.views import login_required_api


@api_view(["GET"])
@login_required_api
def buscar_inventario(request):
    """
    Busca un item de inventario por su número completo.
    No filtra por usuario, busca en toda la base de datos.
    Retorna: inventario, ubicacion (nombre del edificio), recibido_por (nombre del usuario), 
    escuela (nombre de la escuela), foto
    """
    inventario_numero = request.GET.get('inventario', '').strip()
    
    if not inventario_numero:
        return Response(
            {"error": "El parámetro 'inventario' es requerido"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ii.inventario,
                    e.edificio as ubicacion,
                    u.nombre as recibido_por,
                    esc.nombre as escuela,
                    ii.foto
                FROM inventario_items ii
                LEFT JOIN edificios e ON ii.ubicacion_id = e.id
                LEFT JOIN usuarios u ON ii.recibido_por_id = u.id
                LEFT JOIN escuelas esc ON ii.escuela_id = esc.id
                WHERE ii.inventario = %s
            """, [inventario_numero])
            
            row = cursor.fetchone()
            
            if not row:
                return Response(
                    {"success": False, "message": "No se encontró el inventario"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Construir el diccionario con los resultados
            columns = [col[0] for col in cursor.description]
            item = dict(zip(columns, row))
            
            # Construir URL completa de la imagen si existe
            if item.get('foto'):
                # Construir la URL completa usando request para obtener el host
                base_url = request.build_absolute_uri('/')[:-1]  # Remover la barra final
                item['foto_url'] = f"{base_url}{settings.MEDIA_URL}{item['foto']}"
            else:
                item['foto_url'] = None
            
            return Response({
                "success": True,
                "item": item
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response(
            {"error": f"Error al buscar inventario: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(["GET"])
@login_required_api
def listar_edificios(request):
    """
    Retorna una lista de todos los edificios disponibles.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    edificio
                FROM edificios
                ORDER BY edificio
            """)
            
            rows = cursor.fetchall()
            
            # Construir lista de diccionarios
            columns = [col[0] for col in cursor.description]
            edificios = [dict(zip(columns, row)) for row in rows]
            
            return Response({
                "success": True,
                "edificios": edificios,
                "total": len(edificios)
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response(
            {"error": f"Error al obtener edificios: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(["GET"])
@login_required_api
def listar_escuelas(request):
    """
    Retorna una lista de todas las escuelas disponibles.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nombre FROM escuelas ORDER BY nombre")
            rows = cursor.fetchall()
            escuelas = [{"id": r[0], "nombre": r[1]} for r in rows]
            return Response({"success": True, "escuelas": escuelas, "total": len(escuelas)})
    except Exception as e:
        return Response(
            {"error": f"Error al obtener escuelas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )