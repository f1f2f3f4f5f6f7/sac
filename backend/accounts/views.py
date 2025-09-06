import json
import hashlib
import re
import jwt
import datetime
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.conf import settings

# =============================
# Funciones auxiliares
# =============================
def hash_password(password):
    """Hashea la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validar formato de email básico"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_jwt_token(user_id, user_data):
    """Genera un token JWT para el usuario"""
    payload = {
        'user_id': user_id,
        'nombre': user_data[1],
        'email': user_data[2],
        'rol': user_data[3],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),  # 24 horas
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token):
    """Verifica y decodifica un token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required_api(view_func):
    """Decorador para endpoints que requieren token JWT válido"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Obtener el token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Token de autorización requerido'}, status=401)
        
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        
        if not payload:
            return JsonResponse({'error': 'Token inválido o expirado'}, status=401)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nombre, email, rol, activo 
                    FROM usuarios 
                    WHERE id = %s AND activo = true
                """, (payload['user_id'],))
                user = cursor.fetchone()

            if not user:
                return JsonResponse({'error': 'Usuario no encontrado o inactivo'}, status=401)

            request.user_data = user
            request.user_id = payload['user_id']
        except Exception as e:
            return JsonResponse({'error': 'Error de base de datos', 'message': str(e)}, status=500)

        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """Login usando JWT tokens"""
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip().upper()
        password = data.get('password', '')

        if not codigo or not password:
            return JsonResponse({'error': 'Datos incompletos'}, status=400)

        hashed_password = hash_password(password)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.nombre, u.email, u.rol, u.activo, e.nombre
                FROM usuarios u
                LEFT JOIN escuelas e ON u.escuela_id = e.id
                WHERE u.codigo = %s AND u.password_hash = %s AND u.activo = true
            """, (codigo, hashed_password))
            user = cursor.fetchone()

        if not user:
            return JsonResponse({'error': 'Credenciales inválidas'}, status=401)

        # Generar token JWT
        token = generate_jwt_token(user[0], user)

        return JsonResponse({
            'success': True,
            'token': token,
            'user': {
                'id': user[0],
                'codigo': codigo,
                'nombre': user[1],
                'email': user[2],
                'rol': user[3],
                'escuela': user[5]
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Error interno', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    """Vista de logout - con JWT no necesitamos hacer nada en el servidor"""
    return JsonResponse({
        'success': True,
        'message': 'Logout exitoso. El token debe ser eliminado del cliente.'
    })


@login_required_api
@require_http_methods(["GET"])
def profile_view(request):
    """Perfil del usuario"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.codigo, u.nombre, u.email, u.rol, u.activo,
                       e.nombre, e.id
                FROM usuarios u
                LEFT JOIN escuelas e ON u.escuela_id = e.id
                WHERE u.id = %s
            """, (request.user_id,))
            user = cursor.fetchone()

        if not user:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        return JsonResponse({
            'success': True,
            'user': {
                'id': user[0],
                'codigo': user[1],
                'nombre': user[2],
                'email': user[3],
                'rol': user[4],
                'activo': user[5],
                'escuela': {
                    'id': user[7],
                    'nombre': user[6]
                }
            }
        })

    except Exception as e:
        return JsonResponse({'error': 'Error interno', 'message': str(e)}, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    """Registrar usuario usando raw SQL"""
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip().upper()
        nombre = data.get('nombre', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        rol = data.get('rol', 'profesor').lower()
        escuela_id = data.get('escuela_id')

        # Validaciones...
        if not all([codigo, nombre, email, password]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        if not validate_email(email):
            return JsonResponse({'error': 'Email inválido'}, status=400)
        if len(password) < 6:
            return JsonResponse({'error': 'Contraseña muy corta'}, status=400)
        if not re.match(r'^[A-Z0-9]+$', codigo):
            return JsonResponse({'error': 'Código inválido'}, status=400)
        if rol not in ['director', 'profesor']:
            return JsonResponse({'error': 'Rol inválido'}, status=400)

        if escuela_id:
            try:
                escuela_id = int(escuela_id)
            except ValueError:
                return JsonResponse({'error': 'Escuela inválida'}, status=400)

        hashed_password = hash_password(password)

        with connection.cursor() as cursor:
            # Verificaciones...
            cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cursor.fetchone():
                return JsonResponse({'error': 'Email ya registrado'}, status=400)

            cursor.execute("SELECT id FROM usuarios WHERE codigo = %s", (codigo,))
            if cursor.fetchone():
                return JsonResponse({'error': 'Código ya existe'}, status=400)

            if escuela_id:
                cursor.execute("SELECT id FROM escuelas WHERE id = %s", (escuela_id,))
                if not cursor.fetchone():
                    return JsonResponse({'error': 'Escuela no encontrada'}, status=400)

            cursor.execute("""
                INSERT INTO usuarios (codigo, nombre, email, password_hash, rol, escuela_id, activo)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                RETURNING id, codigo, nombre, email, rol
            """, (codigo, nombre, email, hashed_password, rol, escuela_id))
            new_user = cursor.fetchone()

            # ✅ AGREGAR ESTA VALIDACIÓN
            if not new_user:
                return JsonResponse({'error': 'Error al crear usuario'}, status=500)

        return JsonResponse({
            'success': True,
            'user': {
                'id': new_user[0],
                'codigo': new_user[1],
                'nombre': new_user[2],
                'email': new_user[3],
                'rol': new_user[4]
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Error interno', 'message': str(e)}, status=500)