import io
import json
import pandas as pd
from django.db import connection, transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status


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

CATEGORIA_MAP = {
    "Menores": 1,
    "Mayores": 2,
    "Intangible": 3,
}

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
        if file.name.endswith(".xls") or file.name.endswith(".xlsx"):
            read_file = pd.read_excel(file)
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
                dayfirst=True,   # interpreta 29/7/2024 como 29 de julio
            ).dt.strftime("%Y-%m-%d")

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

                    # Buscar id de usuario que entrega
                    entregado_por_id = None
                    entregado_nombre = item.get("funcionario_que_entrega")
                    if entregado_nombre and entregado_nombre.lower() != "nan":
                        cursor.execute(
                            "SELECT id FROM usuarios WHERE LOWER(nombre) = LOWER(%s) LIMIT 1;",
                            [entregado_nombre.strip()]
                        )
                        row = cursor.fetchone()
                        if row:
                            entregado_por_id = row[0]
                        else:
                            not_found_usuarios.append(entregado_nombre.strip())

                    # Buscar id de usuario que recibe
                    recibido_por_id = None
                    recibido_nombre = item.get("funcionario_que_recibe")
                    if recibido_nombre and recibido_nombre.lower() != "nan":
                        cursor.execute(
                            "SELECT id FROM usuarios WHERE LOWER(nombre) = LOWER(%s) LIMIT 1;",
                            [recibido_nombre.strip()]
                        )
                        row = cursor.fetchone()
                        if row:
                            recibido_por_id = row[0]
                        else:
                            not_found_usuarios.append(recibido_nombre.strip())

                    # Siempre dejar escuela en NULL
                    escuela_id = None

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
