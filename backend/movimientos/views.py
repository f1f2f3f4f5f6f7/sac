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
import textwrap
from openpyxl.utils import get_column_letter

def _get_effective_width_chars(ws, coord: str) -> int:
    """
    Devuelve un ancho aproximado en 'caracteres' para la celda coord,
    considerando celdas combinadas (merged). Excel mide column width ~ caracteres.
    """
    # Si está en un merged range, sumamos anchos de columnas del rango
    for r in ws.merged_cells.ranges:
        if coord in r:
            min_col, min_row, max_col, max_row = r.bounds
            total = 0.0
            for c in range(min_col, max_col + 1):
                letter = get_column_letter(c)
                w = ws.column_dimensions[letter].width
                if w is None:
                    w = ws.sheet_format.defaultColWidth or 8.43
                total += float(w)
            return max(1, int(total))

    # No merged: ancho de su columna
    col_letter = "".join(ch for ch in coord if ch.isalpha())
    w = ws.column_dimensions[col_letter].width
    if w is None:
        w = ws.sheet_format.defaultColWidth or 8.43
    return max(1, int(w))


def _count_wrapped_lines(value: str, width_chars: int) -> int:
    """
    Calcula cuántas líneas ocupará un texto envuelto (aprox) usando el ancho en 'caracteres'.
    """
    if value is None:
        return 1
    s = str(value)
    if not s.strip():
        return 1

    width_chars = max(1, int(width_chars))
    total_lines = 0

    # respeta saltos de línea manuales
    for paragraph in s.splitlines() or [""]:
        wrapped = textwrap.wrap(
            paragraph,
            width=width_chars,
            break_long_words=True,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        total_lines += max(1, len(wrapped))

    return max(1, total_lines)


def autofit_row_height(
    ws,
    row: int,
    cols=("B", "D"),
    padding_chars=2,
    max_height=300,
):
    """
    Ajusta la altura de una fila según el contenido (wrap) en las columnas dadas.
    Respeta la altura base del template.
    """
    base = ws.row_dimensions[row].height or ws.sheet_format.defaultRowHeight or 15

    max_lines = 1
    for col in cols:
        coord = f"{col}{row}"
        val = ws[coord].value
        if val:
            width = _get_effective_width_chars(ws, coord)
            width = max(1, width - padding_chars)  # margen
            lines = _count_wrapped_lines(val, width)
            max_lines = max(max_lines, lines)

    ws.row_dimensions[row].height = min(base * max_lines, max_height)

def autofit_row_height_fixed(
    ws,
    row: int,
    cols,
    base_height: float = 15.0,
    padding_chars: int = 2,
    width_factor: float = 0.90,   # <- más conservador (evita subestimar líneas)
    min_height: float | None = None,
    max_height: float = 250.0,
):
    """
    Auto-altura 'tipo Excel' aproximada:
    - IGNORA la altura predefinida del template (clave para que no quede gigante la fila 22).
    - Estima líneas por wrap y fija ws.row_dimensions[row].height.
    """
    max_lines = 1
    for col in cols:
        coord = f"{col}{row}"
        val = ws[coord].value
        if val:
            width = _get_effective_width_chars(ws, coord)
            width = max(1, int((width - padding_chars) * width_factor))
            lines = _count_wrapped_lines(val, width)
            max_lines = max(max_lines, lines)

    height = base_height * max_lines
    if min_height is None:
        min_height = base_height
    ws.row_dimensions[row].height = min(max(height, min_height), max_height)


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

        # Mapear por inventario
        campos_por_inv = {}
        responsables_nombres = set()

        for (
            inventario_pk,
            inventario_num,
            descripcion,
            categoria_id,
            recibido_por_id,
            usuario_nombre,
        ) in rows:
            key = str(inventario_num)
            campos_por_inv[key] = {
                "id": inventario_pk,
                "inventario": inventario_num,
                "descripcion": descripcion,
                "categoria_id": categoria_id,
                "recibido_por_id": recibido_por_id,
                "usuario_nombre": usuario_nombre,
            }
            if usuario_nombre:
                responsables_nombres.add(usuario_nombre)

        # Verificar inventarios no encontrados
        no_encontrados = [inv for inv in inventarios_unicos if inv not in campos_por_inv]
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
            ws = wb.active

        # --- 5. Rellenar cabecera ---
        hoy = date.today()
        ws["B4"] = hoy.strftime("%d/%m/%Y")  # Fecha actual
        ws["C6"] = nombre_responsable        # Campo "De:"

        # --- 6. Rellenar tablas de mayores y menores ---
        fila_mayores = 9    # MAYORES inicia en 9
        fila_menores = 20   # ✅ TU plantilla: MENORES inicia en 20 (no 25)

        filas_usadas = []   # para ajustar alturas luego (opcional)

        for inv in inventarios_unicos:
            data = campos_por_inv[inv]
            desc = data.get("descripcion", "") or ""
            categoria = data.get("categoria_id", 0)
            motivo = motivos_por_inv.get(inv, "") or ""

            if categoria == 2:  # MAYORES
                fila = fila_mayores
                fila_mayores += 1
            else:               # MENORES (categoria 1 u otras)
                fila = fila_menores
                fila_menores += 1

            # Escribir valores
            ws[f"A{fila}"] = inv
            ws[f"B{fila}"] = desc   # B:C está mergeado en el template
            ws[f"D{fila}"] = motivo

            # Wrap + top
            for col in ("B", "D"):
                ws[f"{col}{fila}"].alignment = Alignment(wrap_text=True, vertical="top")

            # ✅ Ajuste de altura de la fila según contenido (sin tocar anchos)
            autofit_row_height(ws, fila, cols=("B", "D"))

            filas_usadas.append(fila)

        # ❌ IMPORTANTE: ya NO ajustamos anchos de columnas para evitar estirar eje X
        # (Elimina el bloque que calculaba ws.column_dimensions[col].width)

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
        now_ts = timezone.now()
        with connection.cursor() as cursor:
            for inv in inventarios_unicos:
                data = campos_por_inv[inv]
                inventario_pk = data["id"]
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
                        request.user_id,  # viene del decorador login_required_api
                        json.dumps(meta_dict),
                    ],
                )

        # --- 9. Responder al cliente con el archivo ---
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
                {"error": "Formato de 'fecha_devolucion' inválido. Usa YYYY-MM-DD."},
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
                {"error": "El campo 'justificacion_prestamo' (o 'justificacion') es obligatorio."},
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
                    {"error": f"Cada item debe tener 'inventario'. Error en posición {idx}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            inventarios.append(inv)
            motivos_por_inv[inv] = mot

        inventarios_unicos = list(dict.fromkeys(inventarios))

        # -------- 3. Consultar inventario_items + usuarios --------
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.id,
                    ii.inventario,
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
                {"error": "No se encontró ningún elemento con esos números de inventario."},
                status=status.HTTP_404_NOT_FOUND,
            )

        campos_por_inv = {}
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
            if usuario_nombre:
                responsables_nombres.add(usuario_nombre)

        no_encontrados = [inv for inv in inventarios_unicos if inv not in campos_por_inv]
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

        wrap_top = Alignment(wrap_text=True, vertical="top")

        # -------- 6. Cabecera --------
        hoy = date.today()
        _set_merged_safe(ws, "D6", _formatear_fecha_ddmmaaaa(hoy))
        _set_merged_safe(ws, "D7", _formatear_fecha_ddmmaaaa(fecha_devolucion))

        _set_merged_safe(ws, "D10", nombre_responsable)
        _set_merged_safe(ws, "D11", unidad_entidad)

        _set_merged_safe(ws, "D14", solicitante_nombre)
        _set_merged_safe(ws, "D15", unidad_entidad)

        _set_merged_safe(ws, "D16", nombre_proyecto, wrap_top)
        _set_merged_safe(ws, "D17", justificacion_prestamo, wrap_top)

        # ✅ Ajusta altura cabecera de forma “como BAJA” (sin multiplicar por altura del template)
        autofit_row_height_fixed(ws, 16, cols=("D",), base_height=15, max_height=120)
        autofit_row_height_fixed(ws, 17, cols=("D",), base_height=15, max_height=180)

        # -------- 7. Tabla elementos a prestar --------
        # En tu plantilla: filas 22–25 son las del detalle.
        fila_actual = 22
        fila_max = 25

        # ✅ MUY IMPORTANTE:
        # Row 22 en el template viene MUY alta (ej: 109.5). La reseteamos antes de calcular.
        for r in range(fila_actual, fila_max + 1):
            ws.row_dimensions[r].height = 15  # base fija y controlada

        for inv in inventarios_unicos:
            if fila_actual > fila_max:
                break

            data_inv = campos_por_inv[inv]
            desc = data_inv["descripcion"]
            marca = data_inv["marca"]
            valor = data_inv["valor"]

            # No. Inventario
            ws[f"A{fila_actual}"] = inv

            # Descripción (B–E merged)
            _set_merged_safe(ws, f"B{fila_actual}", desc, wrap_top)

            # Marca (F–G merged)
            _set_merged_safe(ws, f"F{fila_actual}", marca, wrap_top)

            # Valor compra (H–I merged)
            _set_merged_safe(ws, f"H{fila_actual}", valor)

            # ✅ Auto-altura realista por Descripción + Marca (no toca anchos)
            # - base_height 15: evita la fila gigante
            # - width_factor 0.90: evita subestimar líneas (caso “nombre largo no sube”)
            autofit_row_height_fixed(
                ws,
                fila_actual,
                cols=("B", "F"),
                base_height=15,
                width_factor=0.90,
                max_height=140,
            )

            fila_actual += 1

        # -------- 8. Firmas sección 5 --------
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
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
                cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [user_id])
                row = cursor.fetchone()
                if row:
                    nombre_usuario = row[0] or ""

            # Destinatario por nombre (igual que tú)
            cursor.execute(
                """
                SELECT id, nombre
                FROM usuarios
                WHERE LOWER(nombre) = LOWER(%s)
                """,
                [destinatario_nombre],
            )
            dest_rows = cursor.fetchall()

        if not dest_rows:
            return Response(
                {
                    "error": "El destinatario indicado no existe en la tabla 'usuarios'.",
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
        destinatario_nombre = destinatario_nombre_db

        if not nombre_usuario:
            nombre_usuario = "USUARIO ACTUAL"

        # -------- 4. Consultar inventario_items --------
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.id,
                    ii.inventario,
                    ii.descripcion,
                    ii.categoria_id
                FROM inventario_items ii
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

        campos_por_inv = {}
        for (item_id, inventario, descripcion, categoria_id) in rows:
            campos_por_inv[str(inventario)] = {
                "id": item_id,
                "inventario": inventario,
                "descripcion": descripcion or "",
                "categoria_id": categoria_id,
            }

        no_encontrados = [inv for inv in inventarios_unicos if inv not in campos_por_inv]
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
        wrap_top = Alignment(wrap_text=True, vertical="top")

        # -------- 6. Cabecera --------
        _set_merged_safe(ws, "B5", "Escuela de sistemas")          # U.A.A (B5:C5)
        ws["D5"] = f"Fecha: {fecha_str}"                          # Fecha
        _set_merged_safe(ws, "B7", nombre_usuario)                 # De:
        _set_merged_safe(ws, "B38", f"Nombre: {nombre_usuario}")   # Firma entrega
        _set_merged_safe(ws, "C38", f"Nombre: {destinatario_nombre}")  # Firma recibe

        # -------- 7. Tablas según categoría --------
        # En tu plantilla (según imagen):
        # - MAYORES:   encabezado fila 9, datos 10–18
        # - MENORES:   encabezado fila 20, datos 21–26
        # - INTANGIBLES: encabezado fila 28, datos 29–34 (en tu imagen se ve hasta 34)
        fila_mayores = 10
        fila_menores = 21
        fila_intang  = 29

        consec_mayores = 1
        consec_menores = 1
        consec_intang  = 1

        # ✅ IMPORTANTÍSIMO: limpia cualquier cosa en E/F/G dentro del rango de tablas
        # para que no vuelva a aparecer texto fuera de la tabla.
        for r in range(10, 35):
            for c in ("E", "F", "G", "H"):
                ws[f"{c}{r}"].value = None

        # ✅ También reseteamos alturas base de las filas de tablas a 15
        for r in range(10, 35):
            ws.row_dimensions[r].height = 15

        for inv in inventarios_unicos:
            data = campos_por_inv[inv]
            desc = data["descripcion"]
            categoria = data["categoria_id"]
            motivo = motivos_por_inv[inv]

            texto_elemento = f"{inv} - {desc}"

            if categoria == 2:  # MAYORES
                if fila_mayores > 18:
                    continue

                fila = fila_mayores
                ws[f"A{fila}"] = inv
                # ELEMENTO (B:C merged)
                _set_merged_safe(ws, f"B{fila}", texto_elemento, wrap_top)

                # ✅ MOTIVO DE TRASLADO (D) -> no E
                ws[f"D{fila}"] = motivo
                ws[f"D{fila}"].alignment = wrap_top

                # ✅ Auto-altura por ELEMENTO + MOTIVO (como baja)
                autofit_row_height_fixed(
                    ws, fila, cols=("B", "D"),
                    base_height=15, width_factor=0.90, max_height=140
                )

                fila_mayores += 1
            elif categoria == 1:  # MENORES
                if fila_menores > 26:
                    continue

                fila = fila_menores
                ws[f"A{fila}"] = consec_menores

                _set_merged_safe(ws, f"B{fila}", texto_elemento, wrap_top)

                ws[f"D{fila}"] = motivo
                ws[f"D{fila}"].alignment = wrap_top

                autofit_row_height_fixed(
                    ws, fila, cols=("B", "D"),
                    base_height=15, width_factor=0.90, max_height=140
                )

                fila_menores += 1
                consec_menores += 1

            elif categoria == 3:  # INTANGIBLES
                if fila_intang > 34:   # en tu imagen hay espacio hasta 34
                    continue

                fila = fila_intang
                ws[f"A{fila}"] = consec_intang

                _set_merged_safe(ws, f"B{fila}", texto_elemento, wrap_top)

                ws[f"D{fila}"] = motivo
                ws[f"D{fila}"].alignment = wrap_top

                autofit_row_height_fixed(
                    ws, fila, cols=("B", "D"),
                    base_height=15, width_factor=0.90, max_height=140
                )

                fila_intang += 1
                consec_intang += 1

            else:
                continue

        # -------- 8. Guardar Excel en memoria y en servidor --------
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

        # -------- 9. Registrar trazabilidad --------
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

        # -------- 10. Responder con el archivo --------
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return Response(
            {"error": f"Error al generar la solicitud de traslado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(["GET"])
@login_required_api
def historial_trazabilidad(request):
    """
    Consulta la trazabilidad de movimientos del usuario autenticado.

    Parámetros (query string):

    - tipo / accion (opcional): filtra por tipo de movimiento (columna 'accion')
        Ejemplos de valores según tu implementación actual:
            - "BAJA_SOLICITADA"
            - "Prestamo"
            - "TRASLADO_SOLICITADO"

    - anio / year (opcional): filtrar por año (YYYY)
    - mes / month (opcional): si se envía junto con el año, filtra por año + mes (1–12)

    Ejemplos:
        /api/movimientos/consultar_trazabilidad/                -> todo el historial del usuario
        /api/movimientos/consultar_trazabilidad/?anio=2025      -> todo 2025
        /api/movimientos/consultar_trazabilidad/?anio=2025&mes=3 -> marzo 2025
        /api/movimientos/consultar_trazabilidad/?tipo=Prestamo  -> solo préstamos
    """

    try:
        # --- 1. Identificar usuario actual ---
        user_id = getattr(request, "user_id", None) or getattr(
            getattr(request, "user", None), "id", None
        )
        if not user_id:
            return Response(
                {"error": "No se pudo identificar al usuario autenticado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # --- 2. Leer filtros de query string ---
        qp = request.query_params

        tipo = (qp.get("tipo") or qp.get("accion") or "").strip()
        anio_str = (qp.get("anio") or qp.get("year") or "").strip()
        mes_str = (qp.get("mes") or qp.get("month") or "").strip()

        anio = None
        mes = None

        if anio_str:
            if not anio_str.isdigit():
                return Response(
                    {"error": "El parámetro 'anio/year' debe ser numérico (YYYY)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            anio = int(anio_str)

        if mes_str:
            if not mes_str.isdigit():
                return Response(
                    {"error": "El parámetro 'mes/month' debe ser numérico (1-12)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            mes = int(mes_str)
            if mes < 1 or mes > 12:
                return Response(
                    {"error": "El parámetro 'mes/month' debe estar entre 1 y 12."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not anio:
                return Response(
                    {
                        "error": (
                            "Si filtras por mes, también debes indicar el año "
                            "('anio' o 'year')."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # --- 3. Construir SQL dinámico con filtros ---
        where_clauses = ["t.usuario_id = %s"]
        params = [user_id]

        if tipo:
            where_clauses.append("t.accion = %s")
            params.append(tipo)

        if anio is not None:
            where_clauses.append("EXTRACT(YEAR FROM t.fecha) = %s")
            params.append(anio)

        if mes is not None:
            where_clauses.append("EXTRACT(MONTH FROM t.fecha) = %s")
            params.append(mes)

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT
                t.id,
                t.inventario_id,
                t.fecha,
                t.accion,
                t.detalle,
                t.usuario_id,
                t.meta,
                ii.inventario AS numero_inventario,
                ii.descripcion AS descripcion_item
            FROM inventario_trazabilidad t
            LEFT JOIN inventario_items ii
                   ON t.inventario_id = ii.id
            WHERE {where_sql}
            ORDER BY t.fecha DESC, t.id DESC
        """

        # --- 4. Ejecutar consulta ---
        resultados = []
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # --- 5. Formatear respuesta ---
        for (
            traza_id,
            inventario_id,
            fecha,
            accion,
            detalle,
            usuario_id_db,
            meta_json,
            numero_inventario,
            descripcion_item,
        ) in rows:
            try:
                meta = json.loads(meta_json) if meta_json else {}
            except Exception:
                meta = {"_raw": meta_json}

            resultados.append(
                {
                    "id": traza_id,
                    "inventario_id": inventario_id,
                    "numero_inventario": numero_inventario,
                    "descripcion_item": descripcion_item,
                    "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
                    "accion": accion,
                    "detalle": detalle,
                    "usuario_id": usuario_id_db,
                    "meta": meta,
                }
            )

        return Response(
            {
                "filtros_aplicados": {
                    "tipo": tipo or None,
                    "anio": anio,
                    "mes": mes,
                },
                "total": len(resultados),
                "resultados": resultados,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Error al consultar la trazabilidad: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(["GET"])
@login_required_api
def consultar_trazabilidad_usuario(request):
    """
    Endpoint para DIRECTORES:
    Permite consultar la trazabilidad de cualquier usuario, con filtros opcionales:
    - usuario_id o usuario_nombre (obligatorio UNO de los dos)
    - tipo: baja | prestamo | traslado
    - year: año numérico (ej. 2025)
    - month: mes numérico (1-12)
    """

    try:
        # ---------- 1. Verificar que el solicitante sea DIRECTOR ----------
        requester_id = getattr(request, "user_id", None) or getattr(
            getattr(request, "user", None), "id", None
        )

        if not requester_id:
            return Response(
                {"error": "No se pudo determinar el usuario autenticado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        with connection.cursor() as cursor:
            cursor.execute("SELECT rol FROM usuarios WHERE id = %s", [requester_id])
            row = cursor.fetchone()

        if not row or (row[0] or "").lower() != "director":
            return Response(
                {
                    "error": (
                        "Solo los usuarios con rol 'director' pueden consultar "
                        "la trazabilidad de otros usuarios."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ---------- 2. Determinar el usuario objetivo ----------
        usuario_id_param = (request.GET.get("usuario_id") or "").strip()
        usuario_nombre_param = (request.GET.get("usuario_nombre") or "").strip()

        if not usuario_id_param and not usuario_nombre_param:
            return Response(
                {
                    "error": (
                        "Debes indicar 'usuario_id' o 'usuario_nombre' "
                        "para consultar su trazabilidad."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user_id = None
        target_user_name = None

        with connection.cursor() as cursor:
            if usuario_id_param:
                # Buscar por id
                try:
                    target_user_id = int(usuario_id_param)
                except ValueError:
                    return Response(
                        {"error": "El parámetro 'usuario_id' debe ser numérico."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                cursor.execute(
                    "SELECT nombre FROM usuarios WHERE id = %s",
                    [target_user_id],
                )
                row = cursor.fetchone()
                if not row:
                    return Response(
                        {
                            "error": (
                                "No existe un usuario con el 'usuario_id' indicado."
                            )
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
                target_user_name = row[0]

            else:
                # Buscar por nombre (case-insensitive)
                cursor.execute(
                    """
                    SELECT id, nombre
                    FROM usuarios
                    WHERE LOWER(nombre) = LOWER(%s)
                    """,
                    [usuario_nombre_param],
                )
                rows = cursor.fetchall()

                if not rows:
                    return Response(
                        {
                            "error": (
                                "No se encontró ningún usuario con ese 'usuario_nombre'."
                            )
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                if len(rows) > 1:
                    return Response(
                        {
                            "error": (
                                "Existen varios usuarios con ese nombre. "
                                "Por favor utiliza 'usuario_id'."
                            ),
                            "coincidencias": [r[1] for r in rows],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                target_user_id, target_user_name = rows[0]

        # ---------- 3. Filtros opcionales ----------
        tipo_param = (request.GET.get("tipo") or "").strip().lower()
        year_param = (request.GET.get("year") or "").strip()
        month_param = (request.GET.get("month") or "").strip()

        sql = """
            SELECT
                it.id,
                it.fecha,
                it.accion,
                it.detalle,
                it.meta,
                ii.inventario
            FROM inventario_trazabilidad it
            LEFT JOIN inventario_items ii ON it.inventario_id = ii.id
            WHERE it.usuario_id = %s
        """
        params = [target_user_id]

        # Filtro por tipo (baja | prestamo | traslado)
        if tipo_param:
            acciones = TIPO_ACCION_MAP.get(tipo_param)
            if not acciones:
                return Response(
                    {
                        "error": (
                            "Valor de 'tipo' inválido. Usa: baja, prestamo o traslado."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if len(acciones) == 1:
                sql += " AND it.accion = %s"
                params.append(acciones[0])
            else:
                placeholders = ",".join(["%s"] * len(acciones))
                sql += f" AND it.accion IN ({placeholders})"
                params.extend(acciones)

        # Filtro por año
        if year_param:
            try:
                year_int = int(year_param)
            except ValueError:
                return Response(
                    {"error": "El parámetro 'year' debe ser numérico."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sql += " AND EXTRACT(YEAR FROM it.fecha) = %s"
            params.append(year_int)

        # Filtro por mes
        if month_param:
            try:
                month_int = int(month_param)
            except ValueError:
                return Response(
                    {"error": "El parámetro 'month' debe ser numérico."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not (1 <= month_int <= 12):
                return Response(
                    {
                        "error": (
                            "El parámetro 'month' debe estar entre 1 y 12 (enero–diciembre)."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sql += " AND EXTRACT(MONTH FROM it.fecha) = %s"
            params.append(month_int)

        sql += " ORDER BY it.fecha DESC"

        # ---------- 4. Ejecutar consulta ----------
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        historial = []
        for tz_id, fecha, accion, detalle, meta_json, inventario_num in rows:
            try:
                meta = json.loads(meta_json) if meta_json else None
            except json.JSONDecodeError:
                meta = meta_json  # dejamos el texto crudo si está malformado

            historial.append(
                {
                    "id": tz_id,
                    "fecha": fecha.isoformat() if fecha else None,
                    "accion": accion,
                    "detalle": detalle,
                    "inventario": inventario_num,
                    "meta": meta,
                    "usuario_id": target_user_id,
                    "usuario_nombre": target_user_name,
                }
            )

        return Response(
            {
                "usuario_id": target_user_id,
                "usuario_nombre": target_user_name,
                "total_registros": len(historial),
                "resultados": historial,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Error al consultar la trazabilidad de usuario: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
