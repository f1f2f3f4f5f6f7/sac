@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@login_required_api
def importar_inventario(request):
    """
    Recibe un Excel/CSV y una categoría manual, limpia los datos y hace UPSERT en la tabla inventario_items (optimizado).
    Valida que el usuario autenticado sea el mismo que aparece en la columna 'recibido por'.
    """
    file = request.FILES.get("file")
    categoria_manual = request.data.get("categoria")  # Nueva línea
    
    if not file:
        return Response(
            {"error": "Debes subir un archivo con key 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Validar que se envíe la categoría manualmente
    if not categoria_manual:
        return Response(
            {"error": "Debes enviar la categoría manualmente en el campo 'categoria'. Valores válidos: 'Menores', 'Mayores', 'Intangible'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Validar que la categoría sea válida
    categoria_id = CATEGORIA_MAP.get(categoria_manual.strip())
    if not categoria_id:
        return Response(
            {"error": f"Categoría inválida: '{categoria_manual}'. Valores válidos: 'Menores', 'Mayores', 'Intangible'."},
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

        # --- Usar la categoría manual en lugar de detectarla del archivo ---
        df["Categoría"] = categoria_id  # Usar la categoría enviada manualmente

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
                        item.get("valor"), item.get("fecha_recibido"), categoria_id,  # Usar categoria_id directamente
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
                "categoria_usada": categoria_manual,  # Informar qué categoría se usó
                "ubicaciones_no_encontradas": list(set(not_found_ubicaciones)),
                "usuarios_no_encontrados": list(set(not_found_usuarios))
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)