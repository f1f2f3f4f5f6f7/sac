import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection, transaction
from accounts.views import login_required_api

def registrar_trazabilidad(inventario_id, accion, detalle, usuario_id, meta=None):
    """
    Función auxiliar para registrar acciones en la trazabilidad usando SQL puro
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO inventario_trazabilidad 
            (inventario_id, fecha, accion, detalle, usuario_id, meta)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [
            inventario_id,
            datetime.now(),
            accion,
            detalle,
            usuario_id,
            json.dumps(meta) if meta else None
        ])

@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def crear_prestamo(request):
    """
    Crear un préstamo de un activo - SOLO REGISTRO, NO CAMBIA DUEÑO
    """
    try:
        data = json.loads(request.body)
        inventario_id = data.get('inventario_id')
        usuario_prestatario_id = data.get('usuario_prestatario_id')
        fecha_devolucion_esperada = data.get('fecha_devolucion_esperada')
        observaciones = data.get('observaciones', '')
        
        if not all([inventario_id, usuario_prestatario_id, fecha_devolucion_esperada]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Verificar que el inventario existe y está disponible
                cursor.execute("""
                    SELECT inventario, descripcion, recibido_por_id
                    FROM inventario_items 
                    WHERE id = %s
                """, [inventario_id])
                item = cursor.fetchone()
                
                if not item:
                    return JsonResponse({'error': 'Item de inventario no encontrado'}, status=404)
                
                # Verificar que el usuario autenticado es el responsable del item
                if item[2] != request.user_id:
                    return JsonResponse({
                        'error': 'No tienes permisos para prestar este item'
                    }, status=403)
                
                # Verificar que el usuario prestatario existe
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s AND activo = true", 
                             [usuario_prestatario_id])
                prestatario = cursor.fetchone()
                
                if not prestatario:
                    return JsonResponse({'error': 'Usuario prestatario no encontrado'}, status=404)
                
                # Obtener nombre del prestador (dueño actual)
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [request.user_id])
                prestador = cursor.fetchone()
                
                # NO CAMBIAR EL DUEÑO - Solo registrar en trazabilidad
                meta_data = {
                    'usuario_prestatario_id': usuario_prestatario_id,
                    'usuario_prestatario_nombre': prestatario[0],
                    'usuario_prestador_id': request.user_id,
                    'usuario_prestador_nombre': prestador[0] if prestador else 'Usuario desconocido',
                    'fecha_devolucion_esperada': fecha_devolucion_esperada,
                    'estado': 'prestado',
                    'observaciones': observaciones
                }
                
                registrar_trazabilidad(
                    inventario_id=inventario_id,
                    accion='prestamo',
                    detalle=f"Préstamo de {prestador[0] if prestador else 'Usuario desconocido'} a {prestatario[0]}. Devolución esperada: {fecha_devolucion_esperada}",
                    usuario_id=request.user_id,
                    meta=meta_data
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Préstamo registrado exitosamente - El dueño sigue siendo el mismo',
                    'prestamo': {
                        'inventario': item[0],
                        'descripcion': item[1],
                        'prestatario': prestatario[0],
                        'prestador': prestador[0] if prestador else 'Usuario desconocido',
                        'fecha_devolucion_esperada': fecha_devolucion_esperada,
                        'nota': 'El activo sigue siendo responsabilidad del dueño original'
                    }
                }, status=201)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def crear_traslado(request):
    """
    Crear un traslado de un activo - TRANSFERENCIA COMPLETA DE PROPIEDAD
    """
    try:
        data = json.loads(request.body)
        inventario_id = data.get('inventario_id')
        nuevo_propietario_id = data.get('nuevo_propietario_id')
        observaciones = data.get('observaciones', '')
        
        if not all([inventario_id, nuevo_propietario_id]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Verificar que el inventario existe
                cursor.execute("""
                    SELECT inventario, descripcion, recibido_por_id, entregado_por_id
                    FROM inventario_items 
                    WHERE id = %s
                """, [inventario_id])
                item = cursor.fetchone()
                
                if not item:
                    return JsonResponse({'error': 'Item de inventario no encontrado'}, status=404)
                
                # Verificar que el usuario autenticado es el responsable del item
                if item[2] != request.user_id:
                    return JsonResponse({
                        'error': 'No tienes permisos para transferir este item'
                    }, status=403)
                
                # Verificar que el nuevo propietario existe
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s AND activo = true", 
                             [nuevo_propietario_id])
                nuevo_propietario = cursor.fetchone()
                
                if not nuevo_propietario:
                    return JsonResponse({'error': 'Nuevo propietario no encontrado'}, status=404)
                
                # Obtener nombre del propietario actual
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [request.user_id])
                propietario_actual = cursor.fetchone()
                
                # TRANSFERIR PROPIEDAD COMPLETAMENTE
                cursor.execute("""
                    UPDATE inventario_items 
                    SET recibido_por_id = %s, entregado_por_id = %s
                    WHERE id = %s
                """, [nuevo_propietario_id, request.user_id, inventario_id])
                
                # Registrar en trazabilidad
                meta_data = {
                    'nuevo_propietario_id': nuevo_propietario_id,
                    'nuevo_propietario_nombre': nuevo_propietario[0],
                    'propietario_anterior_id': request.user_id,
                    'propietario_anterior_nombre': propietario_actual[0] if propietario_actual else 'Usuario desconocido',
                    'estado': 'transferido',
                    'observaciones': observaciones
                }
                
                registrar_trazabilidad(
                    inventario_id=inventario_id,
                    accion='traslado',
                    detalle=f"Transferencia completa de {propietario_actual[0] if propietario_actual else 'Usuario desconocido'} a {nuevo_propietario[0]}",
                    usuario_id=request.user_id,
                    meta=meta_data
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Transferencia realizada exitosamente - El activo ahora pertenece al nuevo propietario',
                    'traslado': {
                        'inventario': item[0],
                        'descripcion': item[1],
                        'propietario_anterior': propietario_actual[0] if propietario_actual else 'Usuario desconocido',
                        'nuevo_propietario': nuevo_propietario[0]
                    }
                }, status=201)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def dar_baja_activo(request):
    """
    Dar de baja un activo del inventario
    """
    try:
        data = json.loads(request.body)
        inventario_id = data.get('inventario_id')
        motivo_baja = data.get('motivo_baja')
        observaciones = data.get('observaciones', '')
        
        if not all([inventario_id, motivo_baja]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Verificar que el inventario existe
                cursor.execute("""
                    SELECT inventario, descripcion, recibido_por_id 
                    FROM inventario_items 
                    WHERE id = %s
                """, [inventario_id])
                item = cursor.fetchone()
                
                if not item:
                    return JsonResponse({'error': 'Item de inventario no encontrado'}, status=404)
                
                # Verificar que el usuario autenticado es el responsable del item
                if item[2] != request.user_id:
                    return JsonResponse({
                        'error': 'No tienes permisos para dar de baja este item'
                    }, status=403)
                
                # Registrar en trazabilidad
                meta_data = {
                    'motivo_baja': motivo_baja,
                    'estado': 'completado',
                    'fecha_baja': datetime.now().isoformat(),
                    'observaciones': observaciones
                }
                
                registrar_trazabilidad(
                    inventario_id=inventario_id,
                    accion='baja',
                    detalle=f"Baja del activo. Motivo: {motivo_baja}",
                    usuario_id=request.user_id,
                    meta=meta_data
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Baja del activo registrada exitosamente',
                    'baja': {
                        'inventario': item[0],
                        'descripcion': item[1],
                        'motivo': motivo_baja,
                        'fecha': meta_data['fecha_baja']
                    }
                }, status=201)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def devolver_prestamo(request):
    """
    Devolver un préstamo - SOLO REGISTRO, NO CAMBIA DUEÑO
    """
    try:
        data = json.loads(request.body)
        inventario_id = data.get('inventario_id')
        observaciones = data.get('observaciones', '')
        
        if not inventario_id:
            return JsonResponse({'error': 'ID de inventario requerido'}, status=400)
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Verificar que el inventario existe
                cursor.execute("""
                    SELECT inventario, descripcion, recibido_por_id
                    FROM inventario_items 
                    WHERE id = %s
                """, [inventario_id])
                item = cursor.fetchone()
                
                if not item:
                    return JsonResponse({'error': 'Item de inventario no encontrado'}, status=404)
                
                # Verificar que el usuario autenticado es el dueño del item
                if item[2] != request.user_id:
                    return JsonResponse({
                        'error': 'Solo el dueño del activo puede registrar devoluciones'
                    }, status=403)
                
                # Obtener nombre del dueño
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [request.user_id])
                dueño = cursor.fetchone()
                
                # Solo registrar en trazabilidad - NO cambiar dueño
                meta_data = {
                    'estado': 'devuelto',
                    'fecha_devolucion': datetime.now().isoformat(),
                    'dueño_id': request.user_id,
                    'dueño_nombre': dueño[0] if dueño else 'Usuario desconocido',
                    'observaciones': observaciones
                }
                
                registrar_trazabilidad(
                    inventario_id=inventario_id,
                    accion='devolucion',
                    detalle=f"Devolución registrada por {dueño[0] if dueño else 'Usuario desconocido'}. {observaciones}",
                    usuario_id=request.user_id,
                    meta=meta_data
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Devolución registrada exitosamente',
                    'devolucion': {
                        'inventario': item[0],
                        'descripcion': item[1],
                        'dueño': dueño[0] if dueño else 'Usuario desconocido',
                        'fecha': meta_data['fecha_devolucion'],
                        'nota': 'El activo sigue siendo responsabilidad del dueño original'
                    }
                }, status=201)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@require_http_methods(["GET"])
@login_required_api
def obtener_trazabilidad_inventario(request, inventario_id):
    """
    Obtener el historial de trazabilidad de un item específico
    """
    try:
        with connection.cursor() as cursor:
            # Verificar que el usuario tiene acceso al item
            cursor.execute("""
                SELECT recibido_por_id FROM inventario_items WHERE id = %s
            """, [inventario_id])
            item = cursor.fetchone()
            
            if not item:
                return JsonResponse({'error': 'Item no encontrado'}, status=404)
            
            # Solo el responsable puede ver la trazabilidad
            if item[0] != request.user_id:
                return JsonResponse({
                    'error': 'No tienes permisos para ver la trazabilidad de este item'
                }, status=403)
            
            # Obtener trazabilidad
            cursor.execute("""
                SELECT 
                    it.fecha,
                    it.accion,
                    it.detalle,
                    it.meta,
                    u.nombre as usuario_nombre
                FROM inventario_trazabilidad it
                LEFT JOIN usuarios u ON it.usuario_id = u.id
                WHERE it.inventario_id = %s
                ORDER BY it.fecha DESC
            """, [inventario_id])
            
            trazabilidad = []
            for row in cursor.fetchall():
                trazabilidad.append({
                    'fecha': row[0].isoformat() if row[0] else None,
                    'accion': row[1],
                    'detalle': row[2],
                    'meta': json.loads(row[3]) if row[3] else None,
                    'usuario': row[4]
                })
            
            return JsonResponse({
                'success': True,
                'trazabilidad': trazabilidad,
                'total': len(trazabilidad)
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@require_http_methods(["GET"])
@login_required_api
def obtener_movimientos_usuario(request):
    """
    Obtener todos los movimientos realizados por el usuario autenticado
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    it.fecha,
                    it.accion,
                    it.detalle,
                    it.meta,
                    ii.inventario,
                    ii.descripcion
                FROM inventario_trazabilidad it
                JOIN inventario_items ii ON it.inventario_id = ii.id
                WHERE it.usuario_id = %s
                ORDER BY it.fecha DESC
                LIMIT 100
            """, [request.user_id])
            
            movimientos = []
            for row in cursor.fetchall():
                movimientos.append({
                    'fecha': row[0].isoformat() if row[0] else None,
                    'accion': row[1],
                    'detalle': row[2],
                    'meta': json.loads(row[3]) if row[3] else None,
                    'inventario': row[4],
                    'descripcion': row[5]
                })
            
            return JsonResponse({
                'success': True,
                'movimientos': movimientos,
                'total': len(movimientos)
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)