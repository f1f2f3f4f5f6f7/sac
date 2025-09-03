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

        # renombrar columnas
        df = df[desired_columns]
        df.columns = [normalize_key(c) for c in df.columns]

        data_json = json.loads(df.to_json(orient="records", force_ascii=False))

        # UPSERT en inventario_items
        with transaction.atomic():
            with connection.cursor() as cursor:
                for item in data_json:
                    cursor.execute(
                        """
                        INSERT INTO inventario_items (
                            inventario, descripcion, marca, valor, fecha_recibido,
                            categoria, ubicacion, entregado_por, recibido_por
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (inventario) DO UPDATE SET
                            descripcion = EXCLUDED.descripcion,
                            marca = EXCLUDED.marca,
                            valor = EXCLUDED.valor,
                            fecha_recibido = EXCLUDED.fecha_recibido,
                            categoria = EXCLUDED.categoria,
                            ubicacion = EXCLUDED.ubicacion,
                            entregado_por = EXCLUDED.entregado_por,
                            recibido_por = EXCLUDED.recibido_por;
                        """,
                        [
                            item.get("inventario"),
                            item.get("descripcion"),
                            item.get("marca"),
                            item.get("valor"),
                            item.get("fecha_recibido"),
                            item.get("categoria"),
                            item.get("ubicacion"),
                            item.get("funcionario_que_entrega"),
                            item.get("funcionario_que_recibe"),
                        ],
                    )

        return Response(
            {"status": "ok", "insertados": len(data_json)},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
