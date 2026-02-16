export type GroupedByArchivo = {
  archivo: string;
  ruta_archivo?: string;
  accion: string
  fecha_tramite: string;
  items: Array<{
    numero_inventario: string;
    accion: string;
    descripcion_item: string;
    detalle: string;
    estado: string;
    fecha: string;
    usuario_id: Number 
    meta: {
      foto?: string | null;
    }
  }>;
};