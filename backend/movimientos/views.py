import os
import json
import io
import datetime
from io import BytesIO
from datetime import date
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.db import connection
from django.utils import timezone
from openpyxl import load_workbook
from openpyxl.styles import Alignment
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
        # MUY IMPORTANTE: traemos también ii.id (PK) para usarlo en la trazabilidad
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.id,              -- PK de inventario_items
                    ii.inventario,      -- número de inventario
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

        # Mapear por número de inventario para mantener el orden del request
        # y guardar también el id (PK) real.
        campos_por_inv = {}
        responsables_ids = set()
        responsables_nombres = set()

        for (
            inventario_pk,   # ii.id
            inventario_num,  # ii.inventario
            descripcion,
            categoria_id,
            recibido_por_id,
            usuario_nombre,
        ) in rows:
            campos_por_inv[str(inventario_num)] = {
                "id": inventario_pk,
                "inventario": inventario_num,
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

        # --- 6.1. Ajustar formato: texto envuelto y ancho de columnas ---
        for row in range(9, fila_mayores):  # filas de MAYORES usadas
            for col in ("B", "D"):
                cell = ws[f"{col}{row}"]
                if cell.value:
                    cell.alignment = Alignment(
                        wrap_text=True,
                        vertical="top",
                    )

        for row in range(25, fila_menores):  # filas de MENORES usadas
            for col in ("B", "D"):
                cell = ws[f"{col}{row}"]
                if cell.value:
                    cell.alignment = Alignment(
                        wrap_text=True,
                        vertical="top",
                    )

        for col in ("B", "D"):
            max_len = 0
            for cell in ws[col]:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col].width = min(max_len + 2, 80)

        # --- 7. Guardar en memoria y en servidor ---
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"solicitud_baja_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        media_root = getattr(settings, "MEDIA_ROOT", None)
        file_path = None
        if media_root:
            dest_dir = os.path.join(media_root, "solicitudes_baja")
            os.makedirs(dest_dir, exist_ok=True)
            file_path = os.path.join(dest_dir, filename)
            with open(file_path, "wb") as f:
                f.write(output.getvalue())

        # --- 8. Registrar trazabilidad ---
        # Usamos el id real de inventario_items (inventario_pk) en el campo inventario_id
        now_ts = timezone.now()
        with connection.cursor() as cursor:
            for inv in inventarios_unicos:
                data = campos_por_inv[inv]
                inventario_pk = data["id"]  # ESTE es el que apunta a inventario_items.id
                motivo = motivos_por_inv[inv]

                meta_dict = {
                    "motivo": motivo,
                    "responsable": nombre_responsable,
                    "archivo": filename,
                    "ruta_archivo": file_path,
                }

                cursor.execute(
                    """
                    INSERT INTO inventario_trazabilidad
                        (inventario_id, fecha, accion, detalle, usuario_id, meta)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        inventario_pk,
                        now_ts,
                        "BAJA_SOLICITADA",
                        motivo,
                        request.user_id,          # viene del decorador login_required_api
                        json.dumps(meta_dict),
                    ],
                )

        # --- 9. Responder al cliente con el archivo ---
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return Response(
            {"error": f"Error al generar la solicitud de baja: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )



def _formatear_fecha_ddmmaaaa(fecha: date) -> str:
    """
    Devuelve la fecha con el formato:
    'D: 20   M: 08    A: 2025'
    """
    return f"D: {fecha.day:02d}   M: {fecha.month:02d}    A:  {fecha.year}"


def _set_merged_safe(ws, coord: str, value, alignment: Alignment | None = None):
    """
    Escribe en 'coord'. Si esa celda está dentro de un rango combinado,
    realmente escribe en la esquina superior izquierda de ese rango.
    Así evitamos el error de MergedCell read-only.
    """
    target_coord = coord
    for rng in ws.merged_cells.ranges:
        if coord in rng:
            target_coord = rng.coord.split(":")[0]  # esquina superior izquierda
            break

    cell = ws[target_coord]
    cell.value = value
    if alignment is not None:
        cell.alignment = alignment


@api_view(["POST"])
@login_required_api
def solicitud_prestamo(request):
    """
    Genera el formato de préstamo en Excel y registra la trazabilidad.

    Body esperado (acepta nombres alternos):
    {
        "fecha_devolucion": "2025-08-20",          # YYYY-MM-DD
        "solicitante_nombre": "Juan Pérez",        # o "nombre_solicitante"
        "unidad_entidad": "Facultad de Ingeniería",
        "nombre_proyecto": "Proyecto X",
        "justificacion_prestamo": "Uso temporal...",   # o "justificacion"
        "items": [
            { "inventario": "166718", "motivo": "Uso en capacitación" },
            { "inventario": "164553", "motivo": "Préstamo para pruebas" }
        ]
    }
    """

    try:
        data = request.data

        # -------- 1. Validar campos generales --------
        fecha_devolucion_str = (data.get("fecha_devolucion") or "").strip()
        solicitante_nombre = (
            data.get("solicitante_nombre")
            or data.get("nombre_solicitante")
            or ""
        ).strip()
        unidad_entidad = (data.get("unidad_entidad") or "").strip()
        nombre_proyecto = (data.get("nombre_proyecto") or "").strip()
        justificacion_prestamo = (
            data.get("justificacion_prestamo")
            or data.get("justificacion")
            or ""
        ).strip()
        items = data.get("items")

        if not fecha_devolucion_str:
            return Response(
                {"error": "El campo 'fecha_devolucion' es obligatorio (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            fecha_devolucion = datetime.datetime.strptime(
                fecha_devolucion_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            return Response(
                {
                    "error": (
                        "Formato de 'fecha_devolucion' inválido. "
                        "Usa el formato YYYY-MM-DD, por ejemplo: 2025-08-20."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not solicitante_nombre:
            return Response(
                {"error": "El campo 'solicitante_nombre' (o 'nombre_solicitante') es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not unidad_entidad:
            return Response(
                {"error": "El campo 'unidad_entidad' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not nombre_proyecto:
            return Response(
                {"error": "El campo 'nombre_proyecto' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not justificacion_prestamo:
            return Response(
                {
                    "error": (
                        "El campo 'justificacion_prestamo' "
                        "(o 'justificacion') es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not items or not isinstance(items, list):
            return Response(
                {"error": "Debes enviar una lista 'items' con al menos un elemento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------- 2. Validar items y preparar estructuras --------
        inventarios = []
        motivos_por_inv = {}

        for idx, it in enumerate(items):
            inv = (it.get("inventario") or "").strip()
            mot = (it.get("motivo") or "").strip()
            if not inv:
                return Response(
                    {
                        "error": (
                            "Cada item debe tener 'inventario'. "
                            f"Error en posición {idx}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            inventarios.append(inv)
            motivos_por_inv[inv] = mot

        inventarios_unicos = list(dict.fromkeys(inventarios))  # preserva orden

        # -------- 3. Consultar inventario_items + usuarios --------
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.id,             -- PK inventario_items
                    ii.inventario,     -- No. inventario
                    ii.descripcion,
                    ii.marca,
                    ii.valor,
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
                {
                    "error": (
                        "No se encontró ningún elemento con esos números de inventario."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        campos_por_inv = {}
        responsables_ids = set()
        responsables_nombres = set()

        for (
            item_id,
            inventario,
            descripcion,
            marca,
            valor,
            categoria_id,
            recibido_por_id,
            usuario_nombre,
        ) in rows:
            campos_por_inv[str(inventario)] = {
                "id": item_id,
                "inventario": inventario,
                "descripcion": descripcion or "",
                "marca": marca or "",
                "valor": valor or 0,
                "categoria_id": categoria_id,
                "recibido_por_id": recibido_por_id,
                "usuario_nombre": usuario_nombre or "",
            }
            if recibido_por_id:
                responsables_ids.add(recibido_por_id)
            if usuario_nombre:
                responsables_nombres.add(usuario_nombre)

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

        # -------- 4. Determinar responsable --------
        if not responsables_nombres:
            nombre_responsable = ""
        else:
            if len(responsables_nombres) > 1:
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

        # -------- 5. Cargar plantilla --------
        template_path = os.path.join(
            settings.BASE_DIR,
            "static",
            "plantillas",
            "formato-prestamo.xlsx",
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
            ws = wb.active

        # -------- 6. Cabecera --------
        hoy = date.today()

        _set_merged_safe(ws, "D6", _formatear_fecha_ddmmaaaa(hoy))
        _set_merged_safe(ws, "D7", _formatear_fecha_ddmmaaaa(fecha_devolucion))

        _set_merged_safe(ws, "D10", nombre_responsable)
        _set_merged_safe(ws, "D11", unidad_entidad)

        _set_merged_safe(ws, "D14", solicitante_nombre)
        _set_merged_safe(ws, "D15", unidad_entidad)
        _set_merged_safe(ws, "D16", nombre_proyecto,
                         Alignment(wrap_text=True, vertical="top"))
        _set_merged_safe(ws, "D17", justificacion_prestamo,
                         Alignment(wrap_text=True, vertical="top"))

        # -------- 7. Tabla elementos a prestar --------
        # A: No. Inventario
        # B–E: Descripción
        # F–G: Marca
        # H–I: Valor de compra
        fila_actual = 22
        fila_max = 25

        for inv in inventarios_unicos:
            if fila_actual > fila_max:
                break

            data_inv = campos_por_inv[inv]
            desc = data_inv["descripcion"]
            marca = data_inv["marca"]
            valor = data_inv["valor"]

            # No. Inventario
            ws[f"A{fila_actual}"] = inv

            # Descripción (B–E)
            _set_merged_safe(
                ws,
                f"B{fila_actual}",
                desc,
                Alignment(wrap_text=True, vertical="top")
            )

            # Marca (F–G)
            _set_merged_safe(
                ws,
                f"F{fila_actual}",
                marca,
                Alignment(wrap_text=True, vertical="top")
            )

            # Valor compra (H–I)
            _set_merged_safe(ws, f"H{fila_actual}", valor)

            fila_actual += 1

        # -------- 8. Firmas sección 5 --------
        # Ajusta coordenadas si tu plantilla las tiene en otra fila/columna
        _set_merged_safe(ws, "D28", nombre_responsable)
        _set_merged_safe(ws, "F28", solicitante_nombre)

        # -------- 9. Guardar en memoria y servidor --------
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"solicitud_prestamo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        media_root = getattr(settings, "MEDIA_ROOT", None)
        saved_path = None
        if media_root:
            dest_dir = os.path.join(media_root, "solicitudes_prestamo")
            os.makedirs(dest_dir, exist_ok=True)
            saved_path = os.path.join(dest_dir, filename)
            with open(saved_path, "wb") as f:
                f.write(output.getvalue())

        # -------- 10. Trazabilidad --------
        user_id = getattr(getattr(request, "user", None), "id", None)
        ahora = timezone.now()

        trazas = []
        for inv in inventarios_unicos:
            data_inv = campos_por_inv[inv]
            inventario_pk = data_inv["id"]
            motivo_item = motivos_por_inv.get(inv, "") or ""

            detalle = (
                f"Préstamo de elemento inventario {inv}. "
                f"Solicitante: {solicitante_nombre}. "
                f"Proyecto: {nombre_proyecto}. "
                f"Fecha devolución: {fecha_devolucion_str}. "
                f"Motivo item: {motivo_item}"
            )

            meta = {
                "tipo": "prestamo",
                "inventario": inv,
                "solicitante": solicitante_nombre,
                "unidad_entidad": unidad_entidad,
                "proyecto": nombre_proyecto,
                "justificacion_prestamo": justificacion_prestamo,
                "fecha_devolucion": fecha_devolucion_str,
                "motivo_item": motivo_item,
                "archivo_generado": filename,
                "ruta_archivo": saved_path,
            }

            trazas.append(
                (
                    inventario_pk,
                    ahora,
                    "Prestamo",
                    detalle,
                    user_id,
                    json.dumps(meta, ensure_ascii=False),
                )
            )

        if trazas:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO inventario_trazabilidad
                        (inventario_id, fecha, accion, detalle, usuario_id, meta)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    trazas,
                )

        # -------- 11. Respuesta --------
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return Response(
            {"error": f"Error al generar la solicitud de préstamo: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@login_required_api
def solicitud_traslado(request):
    """
    Genera el formato de TRASLADO en Excel y registra la trazabilidad.

    Body esperado:
    {
        "destinatario_nombre": "Nombre del destinatario",
        "items": [
            { "inventario": "166718", "motivo": "Traslado a laboratorio X" },
            { "inventario": "164553", "motivo": "Reubicación en oficina Y" }
        ]
    }
    """

    try:
        data = request.data

        # -------- 1. Datos generales del POST --------
        destinatario_nombre = (
            data.get("destinatario_nombre")
            or data.get("nombre_destinatario")
            or ""
        ).strip()

        items = data.get("items")

        if not destinatario_nombre:
            return Response(
                {"error": "El campo 'destinatario_nombre' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not items or not isinstance(items, list):
            return Response(
                {"error": "Debes enviar una lista 'items' con al menos un elemento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------- 2. Validar items y preparar estructuras --------
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

        inventarios_unicos = list(dict.fromkeys(inventarios))

        # -------- 3. Obtener datos del usuario actual y destinatario --------
        user_id = getattr(request, "user_id", None) or getattr(
            getattr(request, "user", None), "id", None
        )

        nombre_usuario = ""
        destinatario_id = None

        with connection.cursor() as cursor:
            # Usuario actual (responsable / "De:")
            if user_id:
                cursor.execute(
                    "SELECT nombre FROM usuarios WHERE id = %s",
                    [user_id],
                )
                row = cursor.fetchone()
                if row:
                    nombre_usuario = row[0] or ""

            # Destinatario
            cursor.execute(
                """
                SELECT id, nombre
                FROM usuarios
                WHERE LOWER(nombre) = LOWER(%s)
                """,
                [destinatario_nombre],
            )
            dest_rows = cursor.fetchall()

        if not destinatario_nombre:
            return Response(
                {"error": "Debes indicar el nombre del destinatario."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not dest_rows:
            return Response(
                {
                    "error": (
                        "El destinatario indicado no existe en la tabla 'usuarios'."
                    ),
                    "destinatario": destinatario_nombre,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(dest_rows) > 1:
            return Response(
                {
                    "error": (
                        "Hay más de un usuario con ese nombre. "
                        "Por favor especifica un identificador único."
                    ),
                    "coincidencias": [r[1] for r in dest_rows],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        destinatario_id, destinatario_nombre_db = dest_rows[0]
        # Usamos el nombre tal como está en BD (puede tener mayúsculas, tildes, etc.)
        destinatario_nombre = destinatario_nombre_db

        # Si el usuario actual no está en usuarios, usamos un fallback
        if not nombre_usuario:
            nombre_usuario = "USUARIO ACTUAL"

        # -------- 4. Consultar inventario_items --------
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.id,          -- PK
                    ii.inventario,  -- número de inventario
                    ii.descripcion,
                    ii.categoria_id,
                    ii.serial
                FROM inventario_items ii
                WHERE ii.inventario = ANY(%s)
                """,
                [inventarios_unicos],
            )
            rows = cursor.fetchall()

        if not rows:
            return Response(
                {
                    "error": (
                        "No se encontró ningún elemento con esos números de inventario."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        campos_por_inv = {}
        for (
            item_id,
            inventario,
            descripcion,
            categoria_id,
            serial,
        ) in rows:
            campos_por_inv[str(inventario)] = {
                "id": item_id,
                "inventario": inventario,
                "descripcion": descripcion or "",
                "categoria_id": categoria_id,
                "serial": serial or "",
            }

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

        # -------- 5. Cargar plantilla de TRASLADO --------
        template_path = os.path.join(
            settings.BASE_DIR,
            "static",
            "plantillas",
            "formato-traslado.xlsx",
        )

        if not os.path.exists(template_path):
            return Response(
                {"error": f"No se encontró la plantilla en: {template_path}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        wb = load_workbook(template_path)
        try:
            ws = wb["Traslado"]
        except KeyError:
            ws = wb.active

        hoy = date.today()
        fecha_str = hoy.strftime("%d/%m/%Y")

        # U.A.A -> B5:C5 (combinada)
        _set_merged_safe(ws, "B5", "Escuela de sistemas")

        # Fecha -> D5 (tiene texto 'Fecha: ...')
        # Sobrescribimos con el formato requerido
        ws["D5"] = f"Fecha: {fecha_str}"

        # 'De:' -> B7:D7 (combinada, escribimos en B7)
        _set_merged_safe(ws, "B7", nombre_usuario)

        # Firma responsable (parte inferior) A38:B38  -> 'Nombre: nombre-usuario'
        _set_merged_safe(ws, "B38", f"Nombre: {nombre_usuario}")

        # Firma destinatario C38:D38 -> 'Nombre: nombre-destinatario'
        _set_merged_safe(ws, "C38", f"Nombre: {destinatario_nombre}")

        # -------- 6. Tablas según categoría --------
        # Secciones (filas basadas en tu plantilla):
        #  - Mayores:   encabezado en fila 9, datos 10–18
        #  - Menores:   encabezado en fila 20, datos 21–26
        #  - Intangibles: encabezado en fila 28, datos 29–32

        fila_mayores = 10
        fila_menores = 21
        fila_intang  = 29

        consec_mayores = 1
        consec_menores = 1
        consec_intang  = 1

        for inv in inventarios_unicos:
            data = campos_por_inv[inv]
            desc = data["descripcion"]
            categoria = data["categoria_id"]
            serial = data["serial"]
            motivo = motivos_por_inv[inv]

            # Texto para la columna ELEMENTO
            texto_elemento = f"{inv} - {desc}"

            if categoria == 2:  # MAYORES
                if fila_mayores > 18:
                    # No hay más filas libres en la tabla de mayores
                    continue

                fila = fila_mayores
                ws[f"A{fila}"] = consec_mayores
                _set_merged_safe(
                    ws,
                    f"B{fila}",
                    texto_elemento,
                    Alignment(wrap_text=True, vertical="top"),
                )
                ws[f"D{fila}"] = serial
                ws[f"E{fila}"] = motivo
                ws[f"F{fila}"] = destinatario_nombre
                ws[f"G{fila}"] = "Escuela de sistemas"

                fila_mayores += 1
                consec_mayores += 1

            elif categoria == 1:  # MENORES
                if fila_menores > 26:
                    continue

                fila = fila_menores
                ws[f"A{fila}"] = consec_menores
                _set_merged_safe(
                    ws,
                    f"B{fila}",
                    texto_elemento,
                    Alignment(wrap_text=True, vertical="top"),
                )
                ws[f"D{fila}"] = serial
                ws[f"E{fila}"] = motivo
                ws[f"F{fila}"] = destinatario_nombre
                ws[f"G{fila}"] = "Escuela de sistemas"

                fila_menores += 1
                consec_menores += 1

            elif categoria == 3:  # INTANGIBLES
                if fila_intang > 32:
                    continue

                fila = fila_intang
                ws[f"A{fila}"] = consec_intang
                _set_merged_safe(
                    ws,
                    f"B{fila}",
                    texto_elemento,
                    Alignment(wrap_text=True, vertical="top"),
                )
                ws[f"D{fila}"] = motivo

                fila_intang += 1
                consec_intang += 1

            else:
                # Categoría desconocida -> por ahora la ignoramos
                continue

        # -------- 7. Guardar Excel en memoria y en servidor --------
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"solicitud_traslado_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        media_root = getattr(settings, "MEDIA_ROOT", None)
        saved_path = None
        if media_root:
            dest_dir = os.path.join(media_root, "solicitudes_traslado")
            os.makedirs(dest_dir, exist_ok=True)
            saved_path = os.path.join(dest_dir, filename)
            with open(saved_path, "wb") as f:
                f.write(output.getvalue())

        # -------- 8. Registrar trazabilidad --------
        ahora = timezone.now()
        trazas = []

        for inv in inventarios_unicos:
            data = campos_por_inv[inv]
            inventario_pk = data["id"]
            motivo = motivos_por_inv[inv]

            detalle = (
                f"Traslado de elemento inventario {inv}. "
                f"De: {nombre_usuario}. "
                f"Para: {destinatario_nombre}. "
                f"Motivo: {motivo}"
            )

            meta = {
                "tipo": "traslado",
                "inventario": inv,
                "de": nombre_usuario,
                "destinatario_id": destinatario_id,
                "destinatario_nombre": destinatario_nombre,
                "motivo": motivo,
                "archivo_generado": filename,
                "ruta_archivo": saved_path,
            }

            trazas.append(
                (
                    inventario_pk,
                    ahora,
                    "TRASLADO_SOLICITADO",
                    detalle,
                    user_id,
                    json.dumps(meta, ensure_ascii=False),
                )
            )

        if trazas:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO inventario_trazabilidad
                        (inventario_id, fecha, accion, detalle, usuario_id, meta)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    trazas,
                )

        # -------- 9. Responder con el archivo --------
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return Response(
            {"error": f"Error al generar la solicitud de traslado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
