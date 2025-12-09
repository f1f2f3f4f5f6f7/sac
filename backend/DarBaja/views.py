import os
import json
import io
import datetime
from io import BytesIO
from datetime import date
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from openpyxl import load_workbook
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.views import login_required_api

@api_view(["POST"])
@login_required_api
def solicitud_baja(request):
    """
    Genera el formato de baja en Excel a partir de:
    - inventario (inventario_items.inventario)
    - motivo  (texto libre)
    
    Body:
    {
        "items": [
            { "inventario": "1001", "motivo": "Deterioro" },
            { "inventario": "1002", "motivo": "Pérdida" }
        ]
    }
    """
    
    try:
        items = request.data.get("items")
        if not items or not isinstance(items, list):
            return Response(
                {"error": "Debes enviar una lista 'items' con al menos un elemento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 1. Validar y preparar datos de entrada ---
        inventarios = []
        motivos_por_inv = {}

        for idx, it in enumerate(items):
            inv = (it.get("inventario") or "").strip()
            mot = (it.get("motivo") or "").strip()
            if not inv or not mot:
                return Response(
                    {
                        "error": (
                            "Cada item debe tener 'inventario' y 'motivo'. "
                            f"Error en posición {idx}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            inventarios.append(inv)
            motivos_por_inv[inv] = mot

        inventarios_unicos = list(dict.fromkeys(inventarios))  # preserva orden

        # --- 2. Consultar inventario_items + usuarios ---
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.inventario,
                    ii.descripcion,
                    ii.categoria_id,
                    ii.recibido_por_id,
                    u.nombre AS usuario_nombre
                FROM inventario_items ii
                LEFT JOIN usuarios u ON ii.recibido_por_id = u.id
                WHERE ii.inventario = ANY(%s)
                """,
                [inventarios_unicos],
            )
            rows = cursor.fetchall()

        if not rows:
            return Response(
                {"error": "No se encontró ningún elemento con esos números de inventario."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Mapear por inventario para mantener el orden del request
        campos_por_inv = {}
        responsables_ids = set()
        responsables_nombres = set()

        for inventario, descripcion, categoria_id, recibido_por_id, usuario_nombre in rows:
            campos_por_inv[str(inventario)] = {
                "descripcion": descripcion,
                "categoria_id": categoria_id,
                "recibido_por_id": recibido_por_id,
                "usuario_nombre": usuario_nombre,
            }
            if recibido_por_id:
                responsables_ids.add(recibido_por_id)
            if usuario_nombre:
                responsables_nombres.add(usuario_nombre)

        # Verificar inventarios no encontrados
        no_encontrados = [
            inv for inv in inventarios_unicos if inv not in campos_por_inv
        ]
        if no_encontrados:
            return Response(
                {
                    "error": "Algunos inventarios no existen en la base de datos.",
                    "inventarios_no_encontrados": no_encontrados,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 3. Determinar el nombre para el campo "De:" ---
        if not responsables_nombres:
            nombre_responsable = ""
        else:
            if len(responsables_nombres) > 1:
                # El formato solo tiene un campo "De:", así que obligamos a que todos
                # los ítems pertenezcan al mismo recibido_por_id.
                return Response(
                    {
                        "error": (
                            "Todos los elementos deben tener el mismo responsable "
                            "(recibido_por_id) para poder generar un único formato."
                        ),
                        "responsables_encontrados": list(responsables_nombres),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            nombre_responsable = list(responsables_nombres)[0]

        # --- 4. Cargar la plantilla de Excel ---
        template_path = os.path.join(
            settings.BASE_DIR,
            "static",
            "plantillas",
            "formato-dada-de-baja.xlsx",
        )

        if not os.path.exists(template_path):
            return Response(
                {"error": f"No se encontró la plantilla en: {template_path}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        wb = load_workbook(template_path)
        try:
            ws = wb["Table 1"]
        except KeyError:
            ws = wb.active  # fallback, por si cambia el nombre de la hoja

        # --- 5. Rellenar cabecera ---
        hoy = date.today()
        ws["B4"] = hoy.strftime("%d/%m/%Y")  # Fecha actual (merge B4:C4)
        ws["C6"] = nombre_responsable        # Campo "De:" (merge C6:D6)

        # --- 6. Rellenar tablas de mayores y menores ---
        fila_mayores = 9   # inicio de tabla de elementos MAYORES
        fila_menores = 25  # inicio de tabla de elementos MENORES

        for inv in inventarios_unicos:
            data = campos_por_inv[inv]
            desc = data.get("descripcion", "")
            categoria = data.get("categoria_id", 0)
            motivo = motivos_por_inv.get(inv, "")

            if categoria == 2:  # MAYORES
                fila = fila_mayores
                fila_mayores += 1
            elif categoria == 1:  # MENORES
                fila = fila_menores
                fila_menores += 1
            else:
                # Categoría distinta -> por defecto, se manda a MENORES
                fila = fila_menores
                fila_menores += 1

            ws[f"A{fila}"] = inv    # N° INV
            ws[f"B{fila}"] = desc   # ELEMENTO (B-C unidas en plantilla)
            ws[f"D{fila}"] = motivo # MOTIVO BAJA

        # --- 7. Guardar en memoria, guardar copia en servidor y devolver el archivo ---
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # Nombre de archivo (puedes incluir folio, usuario, etc. si quieres)
        filename = f"solicitud_baja_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # 7.1 Guardar en el servidor (MEDIA_ROOT/solicitudes_baja/)
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root:
            dest_dir = os.path.join(media_root, "solicitudes_baja")
            os.makedirs(dest_dir, exist_ok=True)
            file_path = os.path.join(dest_dir, filename)

            with open(file_path, "wb") as f:
                f.write(output.getvalue())
            # Si quieres, podrías loguear o almacenar file_path en BD.

        # 7.2 Responder al cliente con el archivo
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'
        return response

    except Exception as e:
        return Response(
            {"error": f"Error al generar la solicitud de baja: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
