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
from django.db import connection, transaction



def _formatear_fecha_ddmmaaaa(fecha: date) -> str:
    """
    Devuelve la fecha con el formato:
     DD-MM-YY
    """
    return f"D: {fecha.day:02d}   M: {fecha.month:02d}    A:  {fecha.year}"

def _fecha_dd_mm_yy():
    return timezone.now().strftime("%d-%m-%y")


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

def _crear_notificacion(usuario_id: int, tipo: str, titulo: str, cuerpo: str, meta: dict | None = None):
    meta = meta or {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO notificaciones (usuario_id, tipo, titulo, cuerpo, meta, leida)
            VALUES (%s, %s, %s, %s, %s::jsonb, FALSE)
            RETURNING id
            """,
            [usuario_id, tipo, titulo, cuerpo, json.dumps(meta, ensure_ascii=False)],
        )
        row = cursor.fetchone()
        return row[0] if row else None


def _crear_notificacion_traslado_pendiente(
    destinatario_id: int,
    emisor_id: int,
    emisor_nombre: str,
    destinatario_nombre: str,
    archivo: str,
    ruta_archivo: str | None,
    inventarios: list[str],
):
    titulo = "Traslado pendiente por confirmar"
    cuerpo = (
        f"Tienes un traslado pendiente de {emisor_nombre}. "
        f"Elementos: {len(inventarios)}. Archivo: {archivo}"
    )

    meta = {
        "tipo": "traslado",
        "estado": "pendiente",
        "archivo_generado": archivo,
        "ruta_archivo": ruta_archivo,
        "emisor_id": int(emisor_id),
        "emisor_nombre": emisor_nombre,
        "destinatario_id": int(destinatario_id),
        "destinatario_nombre": destinatario_nombre,
        "inventarios": inventarios,
    }
    return _crear_notificacion(destinatario_id, "traslado_pendiente", titulo, cuerpo, meta)

def _resolve_generated_file_path(ruta_archivo: str | None, archivo: str | None, subdir: str) -> str | None:
    """
    Devuelve una ruta absoluta al archivo generado:
    - Prioriza 'ruta_archivo' (si existe).
    - Si no hay 'ruta_archivo', intenta construirla con MEDIA_ROOT/subdir/archivo.
    """
    ruta_archivo = (ruta_archivo or "").strip()
    archivo = (archivo or "").strip()

    if ruta_archivo:
        # Si ya viene absoluta, perfecto. Si viene relativa, la normalizamos con MEDIA_ROOT.
        if os.path.isabs(ruta_archivo):
            return ruta_archivo
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root:
            return os.path.join(media_root, ruta_archivo)
        return ruta_archivo  # último recurso

    media_root = getattr(settings, "MEDIA_ROOT", None)
    if media_root and archivo:
        return os.path.join(media_root, subdir, archivo)

    return None


def _safe_delete_generated_file(file_path: str | None) -> dict:
    """
    Borra el archivo si existe y si está dentro de MEDIA_ROOT (seguridad).
    Retorna dict con resultado para log / respuesta.
    """
    if not file_path:
        return {"deleted": False, "reason": "no_file_path"}

    media_root = getattr(settings, "MEDIA_ROOT", None)
    try:
        real_path = os.path.realpath(file_path)

        # Seguridad: solo borrar dentro de MEDIA_ROOT si está definido
        if media_root:
            real_media = os.path.realpath(media_root)
            if not (real_path == real_media or real_path.startswith(real_media + os.sep)):
                return {"deleted": False, "reason": "outside_media_root", "path": real_path}

        if not os.path.exists(real_path):
            return {"deleted": False, "reason": "not_found", "path": real_path}

        os.remove(real_path)
        return {"deleted": True, "path": real_path}

    except Exception as e:
        return {"deleted": False, "reason": "exception", "error": str(e), "path": file_path}


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

def _validar_no_movido_completado_por_usuario(user_id: int, item_ids: list[int]):
    """
    Bloquea si alguno de los items ya tiene trazabilidad COMPLETADA del mismo usuario
    con accion = baja o traslado. Prestamo NO bloquea.
    """
    if not user_id or not item_ids:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ii.inventario::text AS numero_inventario,
                t.accion,
                t.fecha
            FROM inventario_trazabilidad t
            JOIN inventario_items ii ON ii.id = t.inventario_id
            WHERE t.usuario_id = %s
              AND t.inventario_id = ANY(%s)
              AND LOWER(COALESCE(t.estado,'')) = 'completado'
              AND LOWER(COALESCE(t.accion,'')) IN ('baja','traslado')
            ORDER BY t.fecha DESC, t.id DESC
            """,
            [user_id, item_ids],
        )
        rows = cursor.fetchall()

    bloqueados = []
    for inv, accion, fecha in rows:
        bloqueados.append(
            {
                "inventario": inv,
                "accion_completada": accion,
                "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
            }
        )
    return bloqueados

def _validar_no_movido_pendiente_por_usuario(user_id: int, item_ids: list[int]):
    """
    Bloquea si alguno de los items ya tiene trazabilidad PENDIENTE del mismo usuario
    con accion = baja o traslado.
    """
    if not user_id or not item_ids:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ii.inventario::text AS numero_inventario,
                t.accion,
                t.fecha
            FROM inventario_trazabilidad t
            JOIN inventario_items ii ON ii.id = t.inventario_id
            WHERE t.usuario_id = %s
              AND t.inventario_id = ANY(%s)
              AND LOWER(COALESCE(t.estado,'')) = 'pendiente'
              AND LOWER(COALESCE(t.accion,'')) IN ('baja','traslado')
            ORDER BY t.fecha DESC, t.id DESC
            """,
            [user_id, item_ids],
        )
        rows = cursor.fetchall()

    return [
        {
            "inventario": inv,
            "accion_pendiente": accion,
            "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
        }
        for inv, accion, fecha in rows
    ]


def _validar_prestamo_activo_por_elemento(item_ids: list[int]):
    """
    Bloquea préstamo si el elemento ya tiene un PRÉSTAMO PENDIENTE
    y la fecha_devolucion (guardada en meta->>'fecha_devolucion') aún no ha llegado.
    Se valida POR ELEMENTO (sin importar usuario) para evitar doble préstamo.
    """
    if not item_ids:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ii.inventario::text AS numero_inventario,
                t.usuario_id,
                t.fecha,
                (to_date(NULLIF(t.meta->>'fecha_devolucion',''), 'YYYY-MM-DD')) AS fecha_devolucion
            FROM inventario_trazabilidad t
            JOIN inventario_items ii ON ii.id = t.inventario_id
            WHERE t.inventario_id = ANY(%s)
              AND LOWER(COALESCE(t.estado,'')) = 'pendiente'
              AND LOWER(COALESCE(t.accion,'')) = 'prestamo'
              AND to_date(NULLIF(t.meta->>'fecha_devolucion',''), 'YYYY-MM-DD') IS NOT NULL
              AND CURRENT_DATE <= to_date(NULLIF(t.meta->>'fecha_devolucion',''), 'YYYY-MM-DD')
            ORDER BY t.fecha DESC, t.id DESC
            """,
            [item_ids],
        )
        rows = cursor.fetchall()

    bloqueados = []
    for inv, usuario_id, fecha, fecha_dev in rows:
        bloqueados.append(
            {
                "inventario": inv,
                "prestamo_usuario_id": usuario_id,
                "fecha_prestamo": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
                "fecha_devolucion": fecha_dev.isoformat() if hasattr(fecha_dev, "isoformat") else str(fecha_dev),
            }
        )
    return bloqueados




@api_view(["POST"])
@login_required_api
def solicitud_baja(request):
    """
    Genera el formato de baja en Excel.
    Bloquea si el item ya tiene BAJA/TRASLADO en estado PENDIENTE para el mismo usuario.
    Registra trazabilidad con estado = 'pendiente'.
    """
    try:
        # ✅ Usuario autenticado
        user_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)
        if not user_id:
            return Response({"error": "No se pudo identificar al usuario autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

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
                    ii.id,
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

        no_encontrados = [inv for inv in inventarios_unicos if inv not in campos_por_inv]
        if no_encontrados:
            return Response(
                {
                    "error": "Algunos inventarios no existen en la base de datos.",
                    "inventarios_no_encontrados": no_encontrados,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ BLOQUEO por PENDIENTE (baja/traslado)
        item_ids = [campos_por_inv[inv]["id"] for inv in inventarios_unicos]
        bloqueados = _validar_no_movido_pendiente_por_usuario(user_id, item_ids)
        if bloqueados:
            return Response(
                {
                    "error": "No puedes generar el movimiento: uno o más elementos ya tienen una BAJA o TRASLADO en estado 'pendiente' para este usuario.",
                    "bloqueados": bloqueados,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # --- 3. Determinar responsable ---
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

        # --- 4. Cargar plantilla ---
        template_path = os.path.join(
            settings.BASE_DIR, "static", "plantillas", "formato-dada-de-baja.xlsx"
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

        # --- 5. Cabecera ---
        hoy = date.today()
        ws["B4"] = hoy.strftime("%d/%m/%Y")
        ws["C6"] = nombre_responsable

        # --- 6. Tablas ---
        fila_mayores = 9
        fila_menores = 20

        for inv in inventarios_unicos:
            data = campos_por_inv[inv]
            desc = data.get("descripcion", "") or ""
            categoria = data.get("categoria_id", 0)
            motivo = motivos_por_inv.get(inv, "") or ""

            if categoria == 2:
                fila = fila_mayores
                fila_mayores += 1
            else:
                fila = fila_menores
                fila_menores += 1

            ws[f"A{fila}"] = inv
            ws[f"B{fila}"] = desc
            ws[f"D{fila}"] = motivo

            for col in ("B", "D"):
                ws[f"{col}{fila}"].alignment = Alignment(wrap_text=True, vertical="top")

            autofit_row_height(ws, fila, cols=("B", "D"))

        # --- 7. Guardar ---
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

        # --- 8. Trazabilidad ---
        now_ts = _fecha_dd_mm_yy()
        with connection.cursor() as cursor:
            for inv in inventarios_unicos:
                inventario_pk = campos_por_inv[inv]["id"]
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
                        (inventario_id, fecha, accion, detalle, usuario_id, meta, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        inventario_pk,
                        now_ts,
                        "baja",
                        motivo,
                        user_id,
                        json.dumps(meta_dict, ensure_ascii=False),
                        "pendiente",
                    ],
                )

        # --- 9. Respuesta ---
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



@api_view(["POST"])
@login_required_api
def solicitud_prestamo(request):
    """
    Genera el formato de préstamo en Excel y registra la trazabilidad.

    BLOQUEOS:
    - Si el item ya tiene BAJA/TRASLADO PENDIENTE para este mismo usuario -> 409
    - Si el item ya tiene PRÉSTAMO PENDIENTE y HOY <= fecha_devolucion -> 409 (por elemento)
    - Si fecha_devolucion < hoy -> 400
    """
    try:
        data = request.data

        # ✅ Usuario autenticado (FIX: ya no queda NULL en trazabilidad)
        user_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)
        if not user_id:
            return Response(
                {"error": "No se pudo identificar al usuario autenticado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # -------- 1. Validar campos generales --------
        fecha_devolucion_str = (data.get("fecha_devolucion") or "").strip()
        solicitante_nombre = (
            data.get("solicitante_nombre") or data.get("nombre_solicitante") or ""
        ).strip()
        unidad_entidad = (data.get("unidad_entidad") or "").strip()
        nombre_proyecto = (data.get("nombre_proyecto") or "").strip()
        justificacion_prestamo = (
            data.get("justificacion_prestamo") or data.get("justificacion") or ""
        ).strip()
        items = data.get("items")

        if not fecha_devolucion_str:
            return Response(
                {"error": "El campo 'fecha_devolucion' es obligatorio (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            fecha_devolucion = datetime.datetime.strptime(fecha_devolucion_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Formato de 'fecha_devolucion' inválido. Usa YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Nuevo: fecha_devolucion no puede estar en el pasado
        hoy = date.today()
        if fecha_devolucion < hoy:
            return Response(
                {
                    "error": "No puedes generar un préstamo con fecha_devolucion en el pasado.",
                    "fecha_devolucion": fecha_devolucion_str,
                    "hoy": hoy.isoformat(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not solicitante_nombre:
            return Response(
                {"error": "El campo 'solicitante_nombre' (o 'nombre_solicitante') es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not unidad_entidad:
            return Response({"error": "El campo 'unidad_entidad' es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        if not nombre_proyecto:
            return Response({"error": "El campo 'nombre_proyecto' es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
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

        item_ids = [campos_por_inv[inv]["id"] for inv in inventarios_unicos]

        # ✅ BLOQUEO 1: BAJA/TRASLADO pendiente para este mismo usuario
        bloqueados_bt = _validar_no_movido_pendiente_por_usuario(user_id, item_ids)
        if bloqueados_bt:
            return Response(
                {
                    "error": (
                        "No puedes generar el préstamo: uno o más elementos ya tienen una "
                        "BAJA o TRASLADO en estado 'pendiente' para este usuario."
                    ),
                    "bloqueados": bloqueados_bt,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # ✅ BLOQUEO 2: PRÉSTAMO activo (pendiente) por elemento y no ha llegado fecha_devolucion
        bloqueados_prestamo = _validar_prestamo_activo_por_elemento(item_ids)
        if bloqueados_prestamo:
            return Response(
                {
                    "error": (
                        "No puedes generar el préstamo: uno o más elementos ya tienen un "
                        "PRÉSTAMO pendiente y la fecha de devolución aún no se cumple."
                    ),
                    "bloqueados": bloqueados_prestamo,
                },
                status=status.HTTP_409_CONFLICT,
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
        _set_merged_safe(ws, "D6", _formatear_fecha_ddmmaaaa(hoy))
        _set_merged_safe(ws, "D7", _formatear_fecha_ddmmaaaa(fecha_devolucion))

        _set_merged_safe(ws, "D10", nombre_responsable)
        _set_merged_safe(ws, "D11", unidad_entidad)

        _set_merged_safe(ws, "D14", solicitante_nombre)
        _set_merged_safe(ws, "D15", unidad_entidad)

        _set_merged_safe(ws, "D16", nombre_proyecto, wrap_top)
        _set_merged_safe(ws, "D17", justificacion_prestamo, wrap_top)

        autofit_row_height_fixed(ws, 16, cols=("D",), base_height=15, max_height=120)
        autofit_row_height_fixed(ws, 17, cols=("D",), base_height=15, max_height=180)

        # -------- 7. Tabla elementos a prestar --------
        fila_actual = 22
        fila_max = 25

        for r in range(fila_actual, fila_max + 1):
            ws.row_dimensions[r].height = 15

        for inv in inventarios_unicos:
            if fila_actual > fila_max:
                break

            data_inv = campos_por_inv[inv]
            desc = data_inv["descripcion"]
            marca = data_inv["marca"]
            valor = data_inv["valor"]

            ws[f"A{fila_actual}"] = inv
            _set_merged_safe(ws, f"B{fila_actual}", desc, wrap_top)
            _set_merged_safe(ws, f"F{fila_actual}", marca, wrap_top)
            _set_merged_safe(ws, f"H{fila_actual}", valor)

            autofit_row_height_fixed(
                ws,
                fila_actual,
                cols=("B", "F"),
                base_height=15,
                width_factor=0.90,
                max_height=140,
            )
            fila_actual += 1

        # -------- 8. Firmas --------
        _set_merged_safe(ws, "D28", nombre_responsable)
        _set_merged_safe(ws, "F28", solicitante_nombre)

        # -------- 9. Guardar en memoria y en servidor --------
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

        # -------- 10. Trazabilidad (FIX usuario_id + estado pendiente) --------
        ahora = _fecha_dd_mm_yy()
        trazas = []

        for inv in inventarios_unicos:
            data_inv = campos_por_inv[inv]
            inventario_pk = data_inv["id"]
            motivo_item = motivos_por_inv.get(inv, "") or ""

            detalle = (
                f"Solicitante: {solicitante_nombre}. "
                f"Fecha devolución: {fecha_devolucion_str}. "
            )

            meta = {
                "tipo": "prestamo",
                "inventario": inv,
                "solicitante": solicitante_nombre,
                "unidad_entidad": unidad_entidad,
                "proyecto": nombre_proyecto,
                "justificacion_prestamo": justificacion_prestamo,
                "fecha_devolucion": fecha_devolucion_str,  # ✅ clave para bloqueo futuro
                "motivo_item": motivo_item,
                "archivo": filename,
                "ruta_archivo": saved_path,
            }

            trazas.append(
                (
                    inventario_pk,
                    ahora,
                    "Prestamo",
                    detalle,
                    user_id,  # ✅ FIX: ya no NULL
                    json.dumps(meta, ensure_ascii=False),
                    "pendiente",
                )
            )

        if trazas:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO inventario_trazabilidad
                        (inventario_id, fecha, accion, detalle, usuario_id, meta, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
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
    Genera el formato de TRASLADO en Excel.

    - Inserta trazabilidad PENDIENTE (accion='traslado', estado='pendiente') para el EMISOR (usuario_id=user_id)
    - Crea notificación 'traslado_pendiente' para el DESTINATARIO (tabla notificaciones)
    - La confirmación del destinatario moverá recibido_por_id al destinatario
    """
    try:
        data = request.data

        # ✅ Usuario autenticado
        user_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)
        if not user_id:
            return Response(
                {"error": "No se pudo identificar al usuario autenticado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        destinatario_nombre = (data.get("destinatario_nombre") or data.get("nombre_destinatario") or "").strip()
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

        # --- 1. Validar items y preparar estructuras ---
        inventarios = []
        motivos_por_inv = {}
        for idx, it in enumerate(items):
            inv = (it.get("inventario") or "").strip()
            mot = (it.get("motivo") or "").strip()
            if not inv or not mot:
                return Response(
                    {"error": f"Cada item debe tener 'inventario' y 'motivo'. Error en posición {idx}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            inventarios.append(inv)
            motivos_por_inv[inv] = mot

        inventarios_unicos = list(dict.fromkeys(inventarios))

        # --- 2. Usuario actual (nombre) y destinatario ---
        nombre_usuario = ""
        destinatario_id = None

        with connection.cursor() as cursor:
            cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", [user_id])
            row = cursor.fetchone()
            if row:
                nombre_usuario = row[0] or ""

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
                {"error": "El destinatario indicado no existe en la tabla 'usuarios'.", "destinatario": destinatario_nombre},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(dest_rows) > 1:
            return Response(
                {"error": "Hay más de un usuario con ese nombre. Por favor especifica un identificador único.", "coincidencias": [r[1] for r in dest_rows]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        destinatario_id, destinatario_nombre_db = dest_rows[0]
        destinatario_nombre = destinatario_nombre_db

        if int(destinatario_id) == int(user_id):
            return Response(
                {"error": "No puedes trasladar elementos a tu mismo usuario."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not nombre_usuario:
            nombre_usuario = "USUARIO ACTUAL"

        # --- 3. inventario_items (incluye recibido_por_id para validar propiedad) ---
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    ii.id,
                    ii.inventario,
                    ii.descripcion,
                    ii.categoria_id,
                    COALESCE(ii.recibido_por_id, 0) AS recibido_por_id
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
        for (item_id, inventario, descripcion, categoria_id, recibido_por_id) in rows:
            campos_por_inv[str(inventario)] = {
                "id": item_id,
                "inventario": inventario,
                "descripcion": descripcion or "",
                "categoria_id": categoria_id,
                "recibido_por_id": int(recibido_por_id or 0),
            }

        no_encontrados = [inv for inv in inventarios_unicos if inv not in campos_por_inv]
        if no_encontrados:
            return Response(
                {"error": "Algunos inventarios no existen en la base de datos.", "inventarios_no_encontrados": no_encontrados},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Validar que todos pertenezcan al emisor
        no_son_del_emisor = []
        for inv in inventarios_unicos:
            if int(campos_por_inv[inv]["recibido_por_id"]) != int(user_id):
                no_son_del_emisor.append(
                    {"inventario": inv, "recibido_por_id_actual": campos_por_inv[inv]["recibido_por_id"]}
                )
        if no_son_del_emisor:
            return Response(
                {
                    "error": "No puedes trasladar elementos que no te pertenecen (recibido_por_id != tu usuario).",
                    "no_son_del_emisor": no_son_del_emisor,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # ✅ BLOQUEO por PENDIENTE (baja/traslado) para el mismo usuario
        item_ids = [campos_por_inv[inv]["id"] for inv in inventarios_unicos]
        bloqueados = _validar_no_movido_pendiente_por_usuario(user_id, item_ids)
        if bloqueados:
            return Response(
                {
                    "error": "No puedes generar el movimiento: uno o más elementos ya tienen una BAJA o TRASLADO en estado 'pendiente' para este usuario.",
                    "bloqueados": bloqueados,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # --- 4. Cargar plantilla ---
        template_path = os.path.join(settings.BASE_DIR, "static", "plantillas", "formato-traslado.xlsx")
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

        # --- 5. Cabecera ---
        _set_merged_safe(ws, "B5", "Escuela de sistemas")
        ws["D5"] = f"Fecha: {fecha_str}"
        _set_merged_safe(ws, "B7", nombre_usuario)
        _set_merged_safe(ws, "B38", f"Nombre: {nombre_usuario}")
        _set_merged_safe(ws, "C38", f"Nombre: {destinatario_nombre}")

        # --- 6. Tablas ---
        fila_mayores = 10
        fila_menores = 21
        fila_intang = 29

        consec_menores = 1
        consec_intang = 1

        for r in range(10, 35):
            for c in ("E", "F", "G", "H"):
                ws[f"{c}{r}"].value = None
            ws.row_dimensions[r].height = 15

        for inv in inventarios_unicos:
            data_item = campos_por_inv[inv]
            desc = data_item["descripcion"]
            categoria = data_item["categoria_id"]
            motivo = motivos_por_inv[inv]

            texto_elemento = f"{inv} - {desc}"

            if categoria == 2:  # MAYORES
                if fila_mayores > 18:
                    continue
                fila = fila_mayores
                ws[f"A{fila}"] = inv
                _set_merged_safe(ws, f"B{fila}", texto_elemento, wrap_top)
                ws[f"D{fila}"] = motivo
                ws[f"D{fila}"].alignment = wrap_top

                autofit_row_height_fixed(ws, fila, cols=("B", "D"), base_height=15, width_factor=0.90, max_height=140)
                fila_mayores += 1

            elif categoria == 1:  # MENORES
                if fila_menores > 26:
                    continue
                fila = fila_menores
                ws[f"A{fila}"] = consec_menores
                _set_merged_safe(ws, f"B{fila}", texto_elemento, wrap_top)
                ws[f"D{fila}"] = motivo
                ws[f"D{fila}"].alignment = wrap_top

                autofit_row_height_fixed(ws, fila, cols=("B", "D"), base_height=15, width_factor=0.90, max_height=140)
                fila_menores += 1
                consec_menores += 1

            elif categoria == 3:  # INTANGIBLES
                if fila_intang > 34:
                    continue
                fila = fila_intang
                ws[f"A{fila}"] = consec_intang
                _set_merged_safe(ws, f"B{fila}", texto_elemento, wrap_top)
                ws[f"D{fila}"] = motivo
                ws[f"D{fila}"].alignment = wrap_top

                autofit_row_height_fixed(ws, fila, cols=("B", "D"), base_height=15, width_factor=0.90, max_height=140)
                fila_intang += 1
                consec_intang += 1

        # --- 7. Guardar ---
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

        # --- 8. Trazabilidad + Notificación (en transacción) ---
        ahora = _fecha_dd_mm_yy()


        with transaction.atomic():
            trazas = []
            for inv in inventarios_unicos:
                inventario_pk = campos_por_inv[inv]["id"]
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
                    "emisor_id": int(user_id),
                    "emisor_nombre": nombre_usuario,
                    "destinatario_id": int(destinatario_id),
                    "destinatario_nombre": destinatario_nombre,
                    "motivo": motivo,
                    "archivo": filename,
                    "ruta_archivo": saved_path,
                }

                trazas.append(
                    (inventario_pk, ahora, "traslado", detalle, user_id, json.dumps(meta, ensure_ascii=False), "pendiente")
                )

            if trazas:
                with connection.cursor() as cursor:
                    cursor.executemany(
                        """
                        INSERT INTO inventario_trazabilidad
                            (inventario_id, fecha, accion, detalle, usuario_id, meta, estado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        trazas,
                    )

            # ✅ Notificación al destinatario
            _crear_notificacion_traslado_pendiente(
                destinatario_id=int(destinatario_id),
                emisor_id=int(user_id),
                emisor_nombre=nombre_usuario,
                destinatario_nombre=destinatario_nombre,
                archivo=filename,
                ruta_archivo=saved_path,
                inventarios=inventarios_unicos,
            )

        # --- 9. Respuesta ---
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
    - anio / year (opcional): filtrar por año (YYYY)
    - mes / month (opcional): si se envía junto con el año, filtra por año + mes (1–12)
    - estado (opcional): filtra por estado de la traza (columna 'estado' en inventario_trazabilidad)
        Valores permitidos: "pendiente" | "completado" (case-insensitive)

    Ejemplos:
        /api/movimientos/consultar_trazabilidad/
        /api/movimientos/consultar_trazabilidad/?anio=2025
        /api/movimientos/consultar_trazabilidad/?anio=2025&mes=3
        /api/movimientos/consultar_trazabilidad/?tipo=Prestamo
        /api/movimientos/consultar_trazabilidad/?estado=pendiente
        /api/movimientos/consultar_trazabilidad/?tipo=traslado&estado=completado
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

        # ✅ NUEVO: estado
        estado = (qp.get("estado") or "").strip().lower()

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

        # ✅ Validación de estado
        if estado:
            estados_validos = {"pendiente", "completado"}
            if estado not in estados_validos:
                return Response(
                    {
                        "error": "El parámetro 'estado' debe ser 'pendiente' o 'completado'.",
                        "estado_recibido": estado,
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

        # ✅ Aplicar filtro por estado (case-insensitive)
        if estado:
            where_clauses.append("LOWER(t.estado) = %s")
            params.append(estado)

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
                t.estado,                           -- ✅ NUEVO: devolver estado
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
            estado_db,            # ✅ NUEVO
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
                    "estado": estado_db,  # ✅ NUEVO
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
                    "estado": estado or None,  # ✅ NUEVO
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
        TIPO_ACCION_MAP = {
            "baja": ["baja"],
            "traslado": ["traslado"],
            "prestamo": ["Prestamo", "prestamo"],
            "préstamo": ["Prestamo", "prestamo"],  # por si te llega con tilde desde frontend
        }
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

@api_view(["GET"])
@login_required_api
def trazabilidad_por_elemento(request):
    """
    Consulta la trazabilidad histórica de UN elemento por número de inventario.
    Incluye movimientos hechos por cualquier usuario.
    Ordena por fecha ASC (del más antiguo al más reciente).

    Query params:
      - inventario (obligatorio): número de inventario del elemento (ej: 166718)

    Ejemplo:
      /api/movimientos/trazabilidad_elemento/?inventario=166718
    """
    try:
        qp = request.query_params
        inventario_num = (qp.get("inventario") or "").strip()

        if not inventario_num:
            return Response(
                {"error": "Debes enviar el parámetro 'inventario' (número de inventario)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1) Encontrar el item por número de inventario
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, inventario, descripcion
                FROM inventario_items
                WHERE inventario = %s
                """,
                [inventario_num],
            )
            item = cursor.fetchone()

        if not item:
            return Response(
                {
                    "error": "No existe un elemento con ese número de inventario.",
                    "inventario": inventario_num,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        item_id, inv_db, descripcion_item = item

        # 2) Traer trazabilidad del item (sin filtrar por usuario)
        query = """
            SELECT
                t.id,
                t.inventario_id,
                t.fecha,
                t.accion,
                t.detalle,
                t.usuario_id,
                t.meta,
                u.nombre as usuario_nombre
            FROM inventario_trazabilidad t
            LEFT JOIN usuarios u ON u.id = t.usuario_id
            WHERE t.inventario_id = %s
            ORDER BY t.fecha ASC, t.id ASC
        """

        resultados = []
        with connection.cursor() as cursor:
            cursor.execute(query, [item_id])
            rows = cursor.fetchall()

        for (
            traza_id,
            inventario_id,
            fecha,
            accion,
            detalle,
            usuario_id,
            meta_json,
            usuario_nombre,
        ) in rows:
            try:
                meta = json.loads(meta_json) if meta_json else {}
            except Exception:
                meta = {"_raw": meta_json}

            resultados.append(
                {
                    "id": traza_id,
                    "inventario_id": inventario_id,
                    "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
                    "accion": accion,
                    "detalle": detalle,
                    "usuario_id": usuario_id,
                    "usuario_nombre": usuario_nombre,
                    "meta": meta,
                }
            )

        return Response(
            {
                "elemento": {
                    "inventario_id": item_id,
                    "numero_inventario": str(inv_db),
                    "descripcion_item": descripcion_item,
                },
                "total": len(resultados),
                "resultados": resultados,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Error al consultar trazabilidad por elemento: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(["POST"])
@login_required_api
def confirmar_o_cancelar_baja(request):
    """
    Confirma o cancela una solicitud de baja agrupada por ARCHIVO (guardado en meta).

    Body JSON:
    {
      "archivo": "solicitud_baja_20260118_204256.xlsx",
      "decision": "confirmar" | "cancelar"
    }
    """
    try:
        data = request.data or {}
        archivo = (data.get("archivo") or "").strip()
        decision = (data.get("decision") or "").strip().lower()

        if not archivo:
            return Response({"error": "El campo 'archivo' es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        if decision not in ("confirmar", "cancelar"):
            return Response({"error": "El campo 'decision' debe ser 'confirmar' o 'cancelar'."}, status=status.HTTP_400_BAD_REQUEST)

        # --- 1) Traer trazas de BAJA pendientes por archivo (meta es JSONB) ---
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    inventario_id,
                    COALESCE(meta->>'ruta_archivo','') AS ruta_archivo
                FROM inventario_trazabilidad
                WHERE accion = %s
                  AND LOWER(estado) = %s
                  AND COALESCE(meta->>'archivo','') = %s
                ORDER BY fecha ASC, id ASC
                """,
                ["baja", "pendiente", archivo],
            )
            rows = cursor.fetchall()

        if not rows:
            return Response(
                {"error": "No se encontraron trazas de baja pendientes para ese archivo.", "archivo": archivo},
                status=status.HTTP_404_NOT_FOUND,
            )

        traza_ids = [r[0] for r in rows]
        item_ids = list({r[1] for r in rows if r[1] is not None})
        ruta_archivo = rows[0][2] if rows else ""

        # Ruta del archivo (si no está en meta, la construimos)
        file_path = _resolve_generated_file_path(
            ruta_archivo=ruta_archivo,
            archivo=archivo,
            subdir="solicitudes_baja",
        )

        ahora = _fecha_dd_mm_yy()
        user_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)

        # --- 2) Ejecutar acción en transacción ---
        if decision == "confirmar":
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE inventario_trazabilidad
                        SET estado = %s
                        WHERE id = ANY(%s)
                        """,
                        ["completado", traza_ids],
                    )

                    if item_ids:
                        cursor.execute(
                            """
                            UPDATE inventario_items
                            SET recibido_por_id = %s
                            WHERE id = ANY(%s)
                            """,
                            [0, item_ids],
                        )

            return Response(
                {
                    "mensaje": "Baja confirmada correctamente.",
                    "archivo": archivo,
                    "trazas_afectadas": len(traza_ids),
                    "items_afectados": len(item_ids),
                    "recibido_por_id_asignado": 0,
                    "fecha": ahora.isoformat(),
                    "usuario_id": user_id,
                },
                status=status.HTTP_200_OK,
            )

        # decision == "cancelar"
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM inventario_trazabilidad WHERE id = ANY(%s)",
                    [traza_ids],
                )

        delete_info = _safe_delete_generated_file(file_path)

        return Response(
            {
                "mensaje": "Baja cancelada y trazabilidad eliminada correctamente.",
                "archivo": archivo,
                "trazas_eliminadas": len(traza_ids),
                "fecha": ahora.isoformat(),
                "usuario_id": user_id,
                "archivo_eliminacion": delete_info,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": f"Error confirmando/cancelando baja: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@login_required_api
def confirmar_cancelar_prestamo(request):
    """
    Confirma o cancela un PRÉSTAMO agrupado por el archivo (meta.archivo_generado).

    Body:
    {
      "archivo": "solicitud_prestamo_20260122_120000.xlsx",
      "accion": "confirmar" | "cancelar"
    }
    """
    try:
        user_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)
        if not user_id:
            return Response({"error": "No se pudo identificar al usuario autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data or {}
        archivo = (data.get("archivo") or "").strip()
        accion = (data.get("accion") or "").strip().lower()

        if not archivo:
            return Response({"error": "Debes enviar 'archivo' (nombre del archivo generado del préstamo)."}, status=status.HTTP_400_BAD_REQUEST)

        if accion not in ("confirmar", "cancelar"):
            return Response({"error": "Debes enviar 'accion' con valor 'confirmar' o 'cancelar'."}, status=status.HTTP_400_BAD_REQUEST)

        # 1) Traer todas las trazas pendientes de préstamo asociadas a ese archivo
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.id,
                    t.inventario_id,
                    ii.inventario::text AS numero_inventario,
                    COALESCE(ii.recibido_por_id, 0) AS recibido_por_id,
                    COALESCE(t.meta->>'ruta_archivo','') AS ruta_archivo
                FROM inventario_trazabilidad t
                JOIN inventario_items ii ON ii.id = t.inventario_id
                WHERE t.usuario_id = %s
                  AND LOWER(COALESCE(t.estado,'')) = 'pendiente'
                  AND LOWER(COALESCE(t.accion,'')) = 'prestamo'
                  AND COALESCE(t.meta->>'archivo_generado', t.meta->>'archivo', '') = %s
                ORDER BY t.fecha ASC, t.id ASC
                """,
                [user_id, archivo],
            )
            rows = cursor.fetchall()

        if not rows:
            return Response(
                {"error": "No se encontraron préstamos pendientes para ese archivo (o ya fueron confirmados/cancelados).", "archivo": archivo},
                status=status.HTTP_404_NOT_FOUND,
            )

        traza_ids = [r[0] for r in rows]
        inventario_ids = [r[1] for r in rows]
        inventarios_nums = [r[2] for r in rows]
        ruta_archivo = rows[0][4] if rows else ""

        # Ruta del archivo (si no está en meta, la construimos)
        file_path = _resolve_generated_file_path(
            ruta_archivo=ruta_archivo,
            archivo=archivo,
            subdir="solicitudes_prestamo",
        )

        if accion == "cancelar":
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM inventario_trazabilidad WHERE id = ANY(%s)", [traza_ids])

            delete_info = _safe_delete_generated_file(file_path)

            return Response(
                {
                    "ok": True,
                    "accion": "cancelar",
                    "archivo": archivo,
                    "total_trazas_eliminadas": len(traza_ids),
                    "inventarios": inventarios_nums,
                    "archivo_eliminacion": delete_info,
                },
                status=status.HTTP_200_OK,
            )

        # accion == "confirmar"
        not_owned = [
            {"inventario": inv_num, "recibido_por_id_actual": rec_id}
            for (_, _, inv_num, rec_id, _) in rows
            if int(rec_id) != int(user_id)
        ]
        if not_owned:
            return Response(
                {
                    "error": "No se puede confirmar el préstamo porque uno o más elementos ya no pertenecen a este usuario (recibido_por_id != usuario actual).",
                    "archivo": archivo,
                    "no_pertenecen_al_usuario": not_owned,
                },
                status=status.HTTP_409_CONFLICT,
            )

        now_ts = _fecha_dd_mm_yy()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE inventario_trazabilidad SET estado = 'completado' WHERE id = ANY(%s)", [traza_ids])
                cursor.execute(
                    """
                    UPDATE inventario_items
                    SET recibido_por_id = 0
                    WHERE id = ANY(%s)
                      AND recibido_por_id = %s
                    """,
                    [inventario_ids, user_id],
                )

        return Response(
            {
                "ok": True,
                "accion": "confirmar",
                "archivo": archivo,
                "total_trazas_confirmadas": len(traza_ids),
                "inventarios": inventarios_nums,
                "fecha_confirmacion": now_ts.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": f"Error al confirmar/cancelar préstamo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@login_required_api
def confirmar_cancelar_traslado(request):
    """
    DESTINATARIO confirma/cancela un traslado agrupado por ARCHIVO.

    Body:
    {
      "archivo": "solicitud_traslado_YYYYMMDD_HHMMSS.xlsx",
      "accion": "confirmar" | "cancelar"
    }
    """
    try:
        receptor_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)
        if not receptor_id:
            return Response({"error": "No se pudo identificar al usuario autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data or {}
        archivo = (data.get("archivo") or "").strip()
        accion = (data.get("accion") or "").strip().lower()

        if not archivo:
            return Response({"error": "Debes enviar 'archivo'."}, status=status.HTTP_400_BAD_REQUEST)

        if accion not in ("confirmar", "cancelar"):
            return Response({"error": "Debes enviar 'accion' como 'confirmar' o 'cancelar'."}, status=status.HTTP_400_BAD_REQUEST)

        # 1) Buscar notificación pendiente (no leída) para este usuario y archivo
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    COALESCE(meta->>'emisor_id','') AS emisor_id_txt,
                    COALESCE(leida, FALSE) AS leida
                FROM notificaciones
                WHERE usuario_id = %s
                  AND tipo = %s
                  AND COALESCE(meta->>'archivo_generado', meta->>'archivo', '') = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                [receptor_id, "traslado_pendiente", archivo],
            )
            notif = cursor.fetchone()

        if not notif:
            return Response({"error": "No existe una notificación de traslado pendiente para este archivo."}, status=status.HTTP_404_NOT_FOUND)

        notif_id, emisor_id_txt, notif_leida = notif
        if notif_leida:
            return Response({"error": "Esta notificación ya fue procesada (leída)."}, status=status.HTTP_409_CONFLICT)

        try:
            emisor_id = int(emisor_id_txt)
        except Exception:
            return Response({"error": "La notificación no tiene un emisor_id válido en meta."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2) Traer trazas pendientes del traslado por archivo y destinatario (usuario_id=emisor)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.id,
                    t.inventario_id,
                    ii.inventario::text AS numero_inventario,
                    COALESCE(ii.recibido_por_id, 0) AS recibido_por_id,
                    COALESCE(t.meta->>'ruta_archivo','') AS ruta_archivo
                FROM inventario_trazabilidad t
                JOIN inventario_items ii ON ii.id = t.inventario_id
                WHERE LOWER(COALESCE(t.accion,'')) = 'traslado'
                  AND LOWER(COALESCE(t.estado,'')) = 'pendiente'
                  AND COALESCE(t.meta->>'archivo_generado', t.meta->>'archivo', '') = %s
                  AND COALESCE(t.meta->>'destinatario_id','') = %s
                  AND COALESCE(t.usuario_id, 0) = %s
                ORDER BY t.fecha ASC, t.id ASC
                """,
                [archivo, str(receptor_id), emisor_id],
            )
            rows = cursor.fetchall()

        if not rows:
            return Response({"error": "No se encontraron trazas pendientes de traslado para ese archivo."}, status=status.HTTP_404_NOT_FOUND)

        traza_ids = [r[0] for r in rows]
        item_ids = [r[1] for r in rows]
        inv_nums = [r[2] for r in rows]
        ruta_archivo = rows[0][4] if rows else ""

        # Ruta del archivo (si no está en meta, la construimos)
        file_path = _resolve_generated_file_path(
            ruta_archivo=ruta_archivo,
            archivo=archivo,
            subdir="solicitudes_traslado",
        )

        now_ts = _fecha_dd_mm_yy()
        patch_meta = {"resultado": accion, "resultado_at": now_ts.isoformat()}

        if accion == "cancelar":
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM inventario_trazabilidad WHERE id = ANY(%s)", [traza_ids])

                    cursor.execute(
                        """
                        UPDATE notificaciones
                        SET leida = TRUE,
                            leida_at = NOW(),
                            meta = meta || %s::jsonb
                        WHERE id = %s
                        """,
                        [json.dumps(patch_meta, ensure_ascii=False), notif_id],
                    )

            delete_info = _safe_delete_generated_file(file_path)

            return Response(
                {
                    "ok": True,
                    "accion": "cancelar",
                    "archivo": archivo,
                    "notificacion_id": notif_id,
                    "trazas_eliminadas": len(traza_ids),
                    "inventarios": inv_nums,
                    "archivo_eliminacion": delete_info,
                },
                status=status.HTTP_200_OK,
            )

        # confirmar: validar que sigan siendo del emisor
        no_son_del_emisor = [
            {"inventario": inv, "recibido_por_id_actual": int(rec_id)}
            for (_, _, inv, rec_id, _) in rows
            if int(rec_id) != int(emisor_id)
        ]
        if no_son_del_emisor:
            return Response(
                {"error": "No se puede confirmar: uno o más items ya no pertenecen al emisor.", "no_son_del_emisor": no_son_del_emisor},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE inventario_trazabilidad SET estado='completado' WHERE id = ANY(%s)", [traza_ids])

                cursor.execute(
                    """
                    UPDATE inventario_items
                    SET recibido_por_id = %s
                    WHERE id = ANY(%s)
                      AND recibido_por_id = %s
                    """,
                    [receptor_id, item_ids, emisor_id],
                )

                cursor.execute(
                    """
                    UPDATE notificaciones
                    SET leida = TRUE,
                        leida_at = NOW(),
                        meta = meta || %s::jsonb
                    WHERE id = %s
                    """,
                    [json.dumps(patch_meta, ensure_ascii=False), notif_id],
                )

        return Response(
            {
                "ok": True,
                "accion": "confirmar",
                "archivo": archivo,
                "notificacion_id": notif_id,
                "trazas_confirmadas": len(traza_ids),
                "items_trasladados": len(item_ids),
                "inventarios": inv_nums,
                "fecha_confirmacion": now_ts.isoformat(),
                "nuevo_propietario": int(receptor_id),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": f"Error al confirmar/cancelar traslado: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@login_required_api
def listar_notificaciones(request):
    """
    /api/movimientos/notificaciones/?leida=false&tipo=traslado_pendiente
    """
    try:
        user_id = getattr(request, "user_id", None) or getattr(getattr(request, "user", None), "id", None)
        if not user_id:
            return Response({"error": "No se pudo identificar al usuario autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

        qp = request.query_params
        leida_param = (qp.get("leida") or "").strip().lower()
        tipo = (qp.get("tipo") or "").strip()

        where = ["usuario_id = %s"]
        params = [user_id]

        if leida_param in ("true", "false"):
            where.append("leida = %s")
            params.append(leida_param == "true")

        if tipo:
            where.append("tipo = %s")
            params.append(tipo)

        where_sql = " AND ".join(where)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, tipo, titulo, cuerpo, meta, leida, created_at, leida_at
                FROM notificaciones
                WHERE {where_sql}
                ORDER BY created_at DESC, id DESC
                """,
                params,
            )
            rows = cursor.fetchall()

        result = []
        for (nid, ntipo, titulo, cuerpo, meta_val, leida, created_at, leida_at) in rows:
            try:
                meta = meta_val if isinstance(meta_val, dict) else (json.loads(meta_val) if meta_val else {})
            except Exception:
                meta = {"_raw": meta_val}

            result.append(
                {
                    "id": nid,
                    "tipo": ntipo,
                    "titulo": titulo,
                    "cuerpo": cuerpo,
                    "meta": meta,
                    "leida": bool(leida),
                    "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                    "leida_at": leida_at.isoformat() if (leida_at and hasattr(leida_at, "isoformat")) else (str(leida_at) if leida_at else None),
                }
            )

        return Response({"total": len(result), "resultados": result}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Error listando notificaciones: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
