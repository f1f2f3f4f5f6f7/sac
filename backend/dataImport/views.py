import io
import json
import pandas as pd
from django.db import connection, transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from accounts.views import login_required_api  # Importar el decorador de autenticación

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

def normalize_name(name: str) -> str:
    """
    Normaliza un nombre quitando espacios y ordenando las palabras,
    para que 'JUAN RAMON PERNALETE' = 'PERNALETE JUAN RAMON'
    """
    return " ".join(sorted(name.strip().lower().split())) if name else None


CATEGORIA_MAP = {
    "Menores": 1,
    "Mayores": 2,
    "Intangible": 3,
}

def get_usuario_id(cursor, nombre):
    if not nombre or str(nombre).lower() == "nan":
        return None  # devolver None para que se maneje arriba

    nombre_norm = nombre.strip()
    print(f"DEBUG: Buscando usuario: '{nombre_norm}'")

    # buscar directo
    cursor.execute(
        "SELECT id, nombre FROM usuarios WHERE LOWER(nombre) = LOWER(%s) LIMIT 1;",
        [nombre_norm]
    )
    row = cursor.fetchone()
    if row:
        print(f"DEBUG: Usuario encontrado directo - ID: {row[0]}, Nombre DB: '{row[1]}'")
        return row[0]

    # buscar invirtiendo orden de palabras
    invertido = " ".join(nombre_norm.split()[::-1])
    print(f"DEBUG: Buscando invertido: '{invertido}'")
    cursor.execute(
        "SELECT id, nombre FROM usuarios WHERE LOWER(nombre) = LOWER(%s) LIMIT 1;",
        [invertido]
    )
    row = cursor.fetchone()
    if row:
        print(f"DEBUG: Usuario encontrado invertido - ID: {row[0]}, Nombre DB: '{row[1]}'")
        return row[0]

    # buscar con LIKE más flexible (cada palabra)
    print(f"DEBUG: Buscando con LIKE flexible para: '{nombre_norm}'")
    palabras = nombre_norm.split()
    condiciones = []
    params = []
    
    for palabra in palabras:
        if len(palabra) > 2:  # solo palabras de más de 2 caracteres
            condiciones.append("LOWER(nombre) LIKE LOWER(%s)")
            params.append(f"%{palabra}%")
    
    if condiciones:
        query = "SELECT id, nombre FROM usuarios WHERE " + " AND ".join(condiciones) + " LIMIT 10;"
        print(f"DEBUG: Query LIKE: {query}")
        print(f"DEBUG: Params LIKE: {params}")
        cursor.execute(query, params)
        similares = cursor.fetchall()
        if similares:
            print(f"DEBUG: Usuarios similares encontrados: {similares}")
            # Si encontramos usuarios similares, tomar el primero como válido
            if similares:
                print(f"DEBUG: Usando usuario similar - ID: {similares[0][0]}, Nombre: '{similares[0][1]}'")
                return similares[0][0]

    print(f"DEBUG: Usuario NO encontrado para: '{nombre_norm}'")
    return 0


def mostrar_usuarios_debug(cursor):
    """Muestra todos los usuarios en la base de datos para debugging"""
    cursor.execute("SELECT id, nombre FROM usuarios ORDER BY nombre LIMIT 20;")
    usuarios = cursor.fetchall()
    print("DEBUG: === LISTA DE USUARIOS EN BASE DE DATOS ===")
    for user_id, nombre in usuarios:
        print(f"DEBUG: ID: {user_id} - Nombre: '{nombre}'")
    print("DEBUG: === FIN LISTA USUARIOS ===")


def validateCategory(nombreArchivo):
    if "Menores" in nombreArchivo:
        return CATEGORIA_MAP["Menores"]
    if "Mayores" in nombreArchivo:
        return CATEGORIA_MAP["Mayores"]
    else:
        return CATEGORIA_MAP["Intangible"]


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def importar_inventario(request):
    """
    Recibe un Excel/CSV, limpia los datos y hace UPSERT en la tabla inventario_items usando SQL crudo.
    """
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"error": "Debes subir un archivo con key 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # leer excel -> csv buffer -> df
        if file.name.endswith(".xlsx"):
            # Para archivos modernos de Excel
            read_file = pd.read_excel(file, engine="openpyxl")
            csv_buffer = io.StringIO()
            read_file.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            df = pd.read_csv(
                csv_buffer,
                skip_blank_lines=True,
                encoding="utf-8",
                header=7,  # fila 8 tiene cabeceras
                skipinitialspace=True,
            )
        elif file.name.endswith(".xls"):
            # Para archivos antiguos de Excel
            read_file = pd.read_excel(file, engine="xlrd")
            csv_buffer = io.StringIO()
            read_file.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            df = pd.read_csv(
                csv_buffer,
                skip_blank_lines=True,
                encoding="utf-8",
                header=7,  # fila 8 tiene cabeceras
                skipinitialspace=True,
            )
        else:  # CSV directo
            df = pd.read_csv(
                file,
                skip_blank_lines=True,
                encoding="utf-8",
                header=7,
                skipinitialspace=True,
            )

        # Asignar categoría
        if "Categoría" not in df.columns:
            df["Categoría"] = validateCategory(file.name)
        else:
            df["Categoría"] = df["Categoría"].apply(
                lambda x: CATEGORIA_MAP.get(str(x).strip(), CATEGORIA_MAP["Intangible"])
            )

        # columnas necesarias
        desired_columns = [
            "Inventario",
            "Descripción",
            "Marca",
            "Valor",
            "Fecha Recibido",
            "Categoría",
            "Ubicación",
            "FUNCIONARIO QUE ENTREGA",
            "FUNCIONARIO QUE RECIBE",
        ]

        df = df.dropna(subset=["Inventario"])
        df = df[df["Inventario"].astype(str).str.strip().str.isnumeric()]

        # limpiar strings
        for col in ["Marca", "Descripción", "FUNCIONARIO QUE ENTREGA", "FUNCIONARIO QUE RECIBE"]:
            df[col] = df[col].astype(str).str.strip()

        # normalizar fechas
        if "Fecha Recibido" in df.columns:
            df["Fecha Recibido"] = pd.to_datetime(
                df["Fecha Recibido"],
                errors="coerce",
                dayfirst=True,
            ).fillna(pd.Timestamp("2000-01-01")).dt.strftime("%Y-%m-%d")

        # limpiar valor ($, ,)
        df["Valor"] = (
            df["Valor"]
            .astype(str)
            .str.replace(r"[^\d.]", "", regex=True)
        )
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

        # renombrar columnas
        df = df[desired_columns]
        df.columns = [normalize_key(c) for c in df.columns]

        data_json = json.loads(df.to_json(orient="records", force_ascii=False))

        not_found_ubicaciones = []
        not_found_usuarios = []

        # UPSERT en inventario_items
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Mostrar lista de usuarios para debugging
                mostrar_usuarios_debug(cursor)
                
                for item in data_json:
                    # Buscar id de edificio según ubicacion
                    ubicacion_id = None
                    ubicacion_nombre = item.get("ubicacion")
                    if ubicacion_nombre:
                        cursor.execute(
                            "SELECT id FROM edificios WHERE LOWER(edificio) = LOWER(%s) LIMIT 1;",
                            [ubicacion_nombre.strip()]
                        )
                        row = cursor.fetchone()
                        if row:
                            ubicacion_id = row[0]
                        else:
                            not_found_ubicaciones.append(ubicacion_nombre.strip())

                    # Buscar usuarios usando la función mejorada
                    entregado_por_id = get_usuario_id(cursor, item.get("funcionario_que_entrega"))
                    recibido_por_id = get_usuario_id(cursor, item.get("funcionario_que_recibe"))

                    # Si no se encuentra el usuario que recibe, saltar este registro
                    if recibido_por_id is None:
                        print(f"DEBUG: Saltando registro por usuario receptor no encontrado: {item.get('funcionario_que_recibe')}")
                        continue

                    # Siempre dejar escuela en NULL
                    escuela_id = 0

                    # UPSERT
                    cursor.execute(
                        """
                        INSERT INTO inventario_items (
                            inventario, descripcion, marca, valor, fecha_recibido,
                            categoria_id, ubicacion_id, entregado_por_id, recibido_por_id,
                            escuela_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (inventario) DO UPDATE SET
                            descripcion = EXCLUDED.descripcion,
                            marca = EXCLUDED.marca,
                            valor = EXCLUDED.valor,
                            fecha_recibido = EXCLUDED.fecha_recibido,
                            categoria_id = EXCLUDED.categoria_id,
                            ubicacion_id = EXCLUDED.ubicacion_id,
                            entregado_por_id = EXCLUDED.entregado_por_id,
                            recibido_por_id = EXCLUDED.recibido_por_id,
                            escuela_id = EXCLUDED.escuela_id;
                        """,
                        [
                            item.get("inventario"),
                            item.get("descripcion"),
                            item.get("marca"),
                            item.get("valor"),
                            item.get("fecha_recibido"),
                            item.get("categoria"),
                            ubicacion_id,
                            entregado_por_id,
                            recibido_por_id,
                            escuela_id,  # siempre nulo
                        ]
                    )

        return Response(
            {
                "status": "ok",
                "insertados": len(data_json),
                "ubicaciones_no_encontradas": list(set(not_found_ubicaciones)),
                "usuarios_no_encontrados": list(set(not_found_usuarios)),
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
@login_required_api
def obtener_inventario_usuario(request):
    """
    Obtiene los items de inventario subidos por el usuario logueado
    """
    try:
        # Obtener el ID del usuario del token JWT
        user_id = request.user_id
        
        with connection.cursor() as cursor:
            # Consulta para obtener los items del inventario del usuario
            cursor.execute("""
                SELECT 
                    ii.inventario,
                    ii.descripcion,
                    ii.marca,
                    ii.valor,
                    ii.fecha_recibido,
                    c.nombre as categoria,
                    e.edificio || ' - ' || s.salones as ubicacion,
                    ue.nombre as entregado_por,
                    ur.nombre as recibido_por,
                    esc.nombre as escuela
                FROM inventario_items ii
                LEFT JOIN categorias c ON ii.categoria_id = c.id
                LEFT JOIN salones s ON ii.ubicacion_id = s.id
                LEFT JOIN edificios e ON s.id_edificio = e.id
                LEFT JOIN usuarios ue ON ii.entregado_por_id = ue.id
                LEFT JOIN usuarios ur ON ii.recibido_por_id = ur.id
                LEFT JOIN escuelas esc ON ii.escuela_id = esc.id
                WHERE ii.recibido_por_id = %s
                ORDER BY ii.fecha_recibido DESC
            """, [user_id])

            
            columns = [col[0] for col in cursor.description]
            items = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return Response({
            "success": True,
            "total_items": len(items),
            "items": items
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": f"Error al obtener inventario: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)