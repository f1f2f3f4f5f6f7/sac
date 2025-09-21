import io
import json
import pandas as pd
import unicodedata
import re
from rapidfuzz import fuzz
from django.db import connection, transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from accounts.views import login_required_api  # Importar el decorador de autenticación
from psycopg2.extras import execute_values


def normalize_key(key: str) -> str:
    return (
        key.strip()
        .lower()
        .replace(" ", "_")
        .replace("ó", "o")
        .replace("í", "i")
        .replace("ú", "u")
        .replace("é", "e")
        .replace("á", "a")
    )

# ================== FUNCIONES DE NOMBRES ==================

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^A-Za-z\s]", "", texto).upper().strip()
    return texto

def dividir_nombre(nombre_completo):
    partes = normalizar_texto(nombre_completo).split()
    num = len(partes)

    if num == 0:
        return {"nombre1": "", "nombre2": "", "apellido1": "", "apellido2": ""}

    elif num == 1:
        return {"nombre1": partes[0], "nombre2": "", "apellido1": "", "apellido2": ""}

    elif num == 2:
        return {
            "nombre1": partes[0],
            "nombre2": "",
            "apellido1": partes[1],
            "apellido2": "",
        }

    elif num == 3:
        return {
            "nombre1": partes[0],
            "nombre2": "",
            "apellido1": partes[1],
            "apellido2": partes[2],
        }

    else:  # 4 o más
        return {
            "nombre1": partes[0],
            "nombre2": partes[1],
            "apellido1": partes[2],
            "apellido2": partes[3],
        }

def comparar_nombres_completos(
    n1,
    n2,
    umbral_global=85,
    umbrales_por_parte={"nombre1": 85, "nombre2": 75, "apellido1": 85, "apellido2": 75},
    doble_error_limite=2,
):
    p1 = dividir_nombre(n1)
    p2 = dividir_nombre(n2)

    scores = {
        "nombre1": fuzz.ratio(p1["nombre1"], p2["nombre1"]),
        "nombre2": fuzz.ratio(p1["nombre2"], p2["nombre2"]),
        "apellido1": fuzz.ratio(p1["apellido1"], p2["apellido1"]),
        "apellido2": fuzz.ratio(p1["apellido2"], p2["apellido2"]),
    }

    similitud_promedio = (
        0.25 * scores["nombre1"]
        + 0.15 * scores["nombre2"]
        + 0.3 * scores["apellido1"]
        + 0.3 * scores["apellido2"]
    )

    campos_en_riesgo = 0
    for parte, umbral in umbrales_por_parte.items():
        score = scores[parte]
        if score < umbral:
            return False, similitud_promedio, scores
        elif umbral <= score < 90:
            campos_en_riesgo += 1

    if campos_en_riesgo >= doble_error_limite:
        return False, similitud_promedio, scores

    return similitud_promedio >= umbral_global, similitud_promedio, scores


# ================== CATEGORÍAS ==================
CATEGORIA_MAP = {
    "Menores": 1,
    "Mayores": 2,
    "Intangible": 3,
}


# ================== CACHE INTELIGENTE DE USUARIOS ==================
class UsuarioCache:
    def __init__(self, cursor):
        self.cursor = cursor
        self.cache_directo = {}  # nombre -> id
        self.cache_invertido = {}  # nombre_invertido -> id
        self.cache_palabras = {}  # palabra -> lista de (id, nombre_completo)
        self.todos_usuarios = []  # lista de (id, nombre) para fuzzy
        self._construir_cache()
    
    def _construir_cache(self):
        """Construye todos los caches de una vez"""
        print("DEBUG: Construyendo cache de usuarios...")
        
        # Obtener todos los usuarios de una vez
        self.cursor.execute("SELECT id, nombre FROM usuarios")
        todos = self.cursor.fetchall()
        
        for user_id, nombre in todos:
            nombre_norm = nombre.strip()
            self.todos_usuarios.append((user_id, nombre_norm))
            
            # Cache directo
            self.cache_directo[nombre_norm.lower()] = user_id
            
            # Cache invertido
            invertido = " ".join(nombre_norm.split()[::-1])
            self.cache_invertido[invertido.lower()] = user_id
            
            # Cache por palabras
            palabras = nombre_norm.split()
            for palabra in palabras:
                if len(palabra) > 2:
                    palabra_key = palabra.lower()
                    if palabra_key not in self.cache_palabras:
                        self.cache_palabras[palabra_key] = []
                    self.cache_palabras[palabra_key].append((user_id, nombre_norm))
        
        print(f"DEBUG: Cache construido - {len(self.todos_usuarios)} usuarios")
    
    def buscar_usuario(self, nombre):
        """Búsqueda optimizada usando caches en memoria"""
        if not nombre or str(nombre).lower() == "nan":
            return None
        
        nombre_norm = nombre.strip()
        print(f"DEBUG: Buscando usuario: '{nombre_norm}'")
        
        # 1. Búsqueda directa
        user_id = self.cache_directo.get(nombre_norm.lower())
        if user_id:
            print(f"DEBUG: Usuario encontrado directo - ID: {user_id}")
            return user_id
        
        # 2. Búsqueda invertida
        invertido = " ".join(nombre_norm.split()[::-1])
        user_id = self.cache_invertido.get(invertido.lower())
        if user_id:
            print(f"DEBUG: Usuario encontrado invertido - ID: {user_id}")
            return user_id
        
        # 3. Búsqueda por palabras (LIKE)
        palabras = nombre_norm.split()
        candidatos = set()
        
        for palabra in palabras:
            if len(palabra) > 2:
                palabra_key = palabra.lower()
                if palabra_key in self.cache_palabras:
                    for user_id, nombre_db in self.cache_palabras[palabra_key]:
                        # Verificar que todas las palabras estén en el nombre de la DB
                        nombre_db_lower = nombre_db.lower()
                        if all(p.lower() in nombre_db_lower for p in palabras):
                            candidatos.add((user_id, nombre_db))
        
        if candidatos:
            # Tomar el primer candidato (más simple que fuzzy para LIKE)
            user_id, nombre_db = list(candidatos)[0]
            print(f"DEBUG: Usuario encontrado por palabras - ID: {user_id}, Nombre: '{nombre_db}'")
            return user_id
        
        # 4. Fuzzy matching (último recurso)
        mejor_match = None
        mejor_score = 0
        
        for user_id, nombre_db in self.todos_usuarios:
            valido, score, _ = comparar_nombres_completos(nombre_norm, nombre_db)
            if valido and score > mejor_score:
                mejor_match = user_id
                mejor_score = score
        
        if mejor_match:
            print(f"DEBUG: Usuario encontrado por FUZZY - ID: {mejor_match}, Score: {mejor_score}")
            return mejor_match
        
        print(f"DEBUG: Usuario NO encontrado para: '{nombre_norm}'")
        return 0


# ================== VALIDACION CATEGORÍA ==================
def validateCategory(nombreArchivo):
    if "Menores" in nombreArchivo:
        return CATEGORIA_MAP["Menores"]
    if "Mayores" in nombreArchivo:
        return CATEGORIA_MAP["Mayores"]
    else:
        return CATEGORIA_MAP["Intangible"]


# ================== IMPORTAR INVENTARIO ==================
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@login_required_api  # Agregar el decorador de autenticación
def importar_inventario(request):
    """
    Recibe un Excel/CSV, limpia los datos y hace UPSERT en la tabla inventario_items (optimizado).
    Valida que el usuario autenticado sea el mismo que aparece en la columna 'recibido por'.
    """
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"error": "Debes subir un archivo con key 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # --- Lectura del archivo (usando el método que funciona) ---
        if file.name.endswith(".xlsx"):
            read_file = pd.read_excel(file, engine="openpyxl")
            csv_buffer = io.StringIO()
            read_file.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            df = pd.read_csv(csv_buffer, skip_blank_lines=True, encoding="utf-8", header=7, skipinitialspace=True)
        elif file.name.endswith(".xls"):
            read_file = pd.read_excel(file, engine="xlrd")
            csv_buffer = io.StringIO()
            read_file.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            df = pd.read_csv(csv_buffer, skip_blank_lines=True, encoding="utf-8", header=7, skipinitialspace=True)
        else:
            df = pd.read_csv(file, skip_blank_lines=True, encoding="utf-8", header=7, skipinitialspace=True)

        # --- Categoría ---
        if "Categoría" not in df.columns:
            df["Categoría"] = validateCategory(file.name)
        else:
            df["Categoría"] = df["Categoría"].apply(
                lambda x: CATEGORIA_MAP.get(str(x).strip(), CATEGORIA_MAP["Intangible"])
            )

        # --- Limpieza ---
        desired_columns = [
            "Inventario", "Descripción", "Marca", "Valor", "Fecha Recibido", "Categoría",
            "Ubicación", "FUNCIONARIO QUE ENTREGA", "FUNCIONARIO QUE RECIBE"
        ]

        df = df.dropna(subset=["Inventario"])
        df = df[df["Inventario"].astype(str).str.strip().str.isnumeric()]

        for col in ["Marca", "Descripción", "FUNCIONARIO QUE ENTREGA", "FUNCIONARIO QUE RECIBE"]:
            df[col] = df[col].astype(str).str.strip()

        if "Fecha Recibido" in df.columns:
            df["Fecha Recibido"] = (
                pd.to_datetime(df["Fecha Recibido"], errors="coerce", dayfirst=True)
                .fillna(pd.Timestamp("2000-01-01"))
                .dt.strftime("%Y-%m-%d")
            )

        df["Valor"] = df["Valor"].astype(str).str.replace(r"[^\d.]", "", regex=True)
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

        df = df[desired_columns]
        df.columns = [normalize_key(c) for c in df.columns]
        data_json = json.loads(df.to_json(orient="records", force_ascii=False))

        # === VALIDACIÓN DE USUARIO AUTENTICADO ===
        with connection.cursor() as cursor:
            # Obtener el nombre del usuario autenticado
            cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [request.user_id])
            usuario_autenticado = cursor.fetchone()
            
            if not usuario_autenticado:
                return Response(
                    {"error": "Usuario no encontrado en la base de datos."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            nombre_usuario_autenticado = usuario_autenticado[0]
            print(f"DEBUG: Usuario autenticado: '{nombre_usuario_autenticado}'")
            
            # Crear cache de usuarios para validación
            usuario_cache = UsuarioCache(cursor)
            
            # Validar que todos los registros tengan el mismo usuario en "recibido por"
            # Usar IDs de usuario en lugar de nombres para la comparación
            usuarios_recibidos_ids = set()
            usuarios_recibidos_nombres = set()
            
            for item in data_json:
                recibido_por = item.get("funcionario_que_recibe", "").strip()
                if recibido_por:
                    usuarios_recibidos_nombres.add(recibido_por)
                    # Buscar el ID del usuario usando la misma lógica de búsqueda
                    usuario_id = usuario_cache.buscar_usuario(recibido_por)
                    if usuario_id and usuario_id != 0:
                        usuarios_recibidos_ids.add(usuario_id)
            
            # Verificar que solo haya un usuario único en "recibido por" (por ID)
            if len(usuarios_recibidos_ids) > 1:
                return Response(
                    {
                        "error": "Todos los registros deben tener el mismo usuario en la columna 'FUNCIONARIO QUE RECIBE'.",
                        "usuarios_encontrados": list(usuarios_recibidos_nombres)
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Verificar que el usuario en "recibido por" coincida con el usuario autenticado
            if usuarios_recibidos_ids:
                usuario_id_en_archivo = list(usuarios_recibidos_ids)[0]
                
                if usuario_id_en_archivo != request.user_id:
                    # Obtener el nombre del usuario encontrado en el archivo para el mensaje de error
                    cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [usuario_id_en_archivo])
                    usuario_encontrado = cursor.fetchone()
                    nombre_usuario_encontrado = usuario_encontrado[0] if usuario_encontrado else "Usuario desconocido"
                    
                    return Response(
                        {
                            "error": f"El usuario en el archivo ('{nombre_usuario_encontrado}') no coincide con tu usuario autenticado ('{nombre_usuario_autenticado}').",
                            "usuario_archivo": nombre_usuario_encontrado,
                            "usuario_autenticado": nombre_usuario_autenticado
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        not_found_ubicaciones, not_found_usuarios = [], []
        nuevos, repetidos = [], []

        with transaction.atomic():
            with connection.cursor() as cursor:
                # === Cache de edificios ===
                cursor.execute("SELECT id, LOWER(edificio) FROM edificios")
                edificios_map = {nombre.strip().lower(): eid for eid, nombre in cursor.fetchall()}

                # === Cache inteligente de usuarios ===
                usuario_cache = UsuarioCache(cursor)

                # === Preparar registros para batch insert ===
                records = []
                for item in data_json:
                    # Ubicación
                    ubicacion_id = None
                    if item.get("ubicacion"):
                        ubicacion_id = edificios_map.get(item["ubicacion"].strip().lower())
                        if not ubicacion_id:
                            not_found_ubicaciones.append(item["ubicacion"].strip())

                    # Usuarios - usar cache optimizado
                    entregado_por_id = usuario_cache.buscar_usuario(item.get("funcionario_que_entrega", ""))
                    recibido_por_id = usuario_cache.buscar_usuario(item.get("funcionario_que_recibe", ""))

                    if recibido_por_id is None or recibido_por_id == 0:  # si no existe, marcar
                        not_found_usuarios.append(item.get("funcionario_que_recibe"))
                        continue

                    # Agregar al batch
                    records.append((
                        item.get("inventario"), item.get("descripcion"), item.get("marca"),
                        item.get("valor"), item.get("fecha_recibido"), item.get("categoria"),
                        ubicacion_id, entregado_por_id, recibido_por_id, 0  # escuela_id
                    ))

                # === Batch UPSERT ===
                if records:
                    execute_values(cursor, """
                        INSERT INTO inventario_items (
                            inventario, descripcion, marca, valor, fecha_recibido,
                            categoria_id, ubicacion_id, entregado_por_id, recibido_por_id, escuela_id
                        )
                        VALUES %s
                        ON CONFLICT (inventario) DO UPDATE SET
                            descripcion = EXCLUDED.descripcion,
                            marca = EXCLUDED.marca,
                            valor = EXCLUDED.valor,
                            fecha_recibido = EXCLUDED.fecha_recibido,
                            categoria_id = EXCLUDED.categoria_id,
                            ubicacion_id = EXCLUDED.ubicacion_id,
                            entregado_por_id = EXCLUDED.entregado_por_id,
                            recibido_por_id = EXCLUDED.recibido_por_id,
                            escuela_id = EXCLUDED.escuela_id
                        """,
                        records
                    )

        return Response(
            {
                "status": "ok",
                "procesados": len(records),
                "ubicaciones_no_encontradas": list(set(not_found_ubicaciones)),
                "usuarios_no_encontrados": list(set(not_found_usuarios))
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================== OBTENER INVENTARIO ==================
@api_view(["GET"])
@login_required_api
def obtener_inventario_usuario(request):
    try:
        user_id = request.user_id
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ii.inventario, ii.descripcion, ii.marca, ii.valor, ii.fecha_recibido,
                    c.nombre as categoria, e.edificio as ubicacion,
                    ue.nombre as entregado_por, ur.nombre as recibido_por, esc.nombre as escuela
                FROM inventario_items ii
                LEFT JOIN categorias c ON ii.categoria_id = c.id
                LEFT JOIN edificios e ON ii.ubicacion_id = e.id
                LEFT JOIN usuarios ue ON ii.entregado_por_id = ue.id
                LEFT JOIN usuarios ur ON ii.recibido_por_id = ur.id
                LEFT JOIN escuelas esc ON ii.escuela_id = esc.id
                WHERE ii.recibido_por_id = %s
                ORDER BY ii.fecha_recibido DESC
            """, [user_id])

            columns = [col[0] for col in cursor.description]
            items = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response({"success": True, "total_items": len(items), "items": items}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Error al obtener inventario: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)