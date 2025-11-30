export interface IInventaryItem {
    categoria: string;
    descripcion: string;
    entregado_por: string;
    escuela: string;
    serial: string
    fecha_recibido: string;
    inventario: string;
    inventoried: boolean;
    marca: string;
    recibido_por: string;
    ubicacion: string;
    valor: number;
    foto: string
}


export interface IBusquedaGeneralResult {
    inventario: string;
    ubicacion: string | null;
    recibido_por: string | null;
    escuela: string | null;
    foto: string | null;
    foto_url: string | null;
  }
  