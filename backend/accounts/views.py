import json
import hashlib
import re
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection

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

def login_required_api(view_func):
    """Decorador para endpoints que requieren sesión activa"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Autenticación requerida'}, status=401)

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nombre, email, rol, activo 
                    FROM usuarios 
                    WHERE id = %s AND activo = true
                """, (user_id,))
                user = cursor.fetchone()

            if not user:
                request.session.flush()
                return JsonResponse({'error': 'Sesión inválida'}, status=401)

            request.user_data = user
        except Exception as e:
            return JsonResponse({'error': 'Error de base de datos', 'message': str(e)}, status=500)

        return view_func(request, *args, **kwargs)
    return wrapper

# =============================
# Vistas
# =============================
@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """Login usando raw SQL"""
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

        # Crear sesión
        request.session['user_id'] = user[0]
        request.session['user_name'] = user[1]
        request.session['user_email'] = user[2]
        request.session['user_role'] = user[3]
        request.session.set_expiry(86400)  # 24 horas

        return JsonResponse({
            'success': True,
            'user': {
                'id': user[0],
                'codigo': user[1],  # <-- Cambié 'nombre' por 'codigo' aquí
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
    """Vista de logout que cierra la sesión"""
    try:
        # Limpiar la sesión
        request.session.flush()
        
        return JsonResponse({
            'success': True,
            'message': 'Sesión cerrada exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Error al cerrar sesión',
            'message': str(e)
        }, status=500)

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
            """, (request.session['user_id'],))
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