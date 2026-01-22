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
    observations: string
    edificio?: string;
    salon: string;
    valor: number;
    foto: string
    imagen_url: string | null;
}


export type IInvetaryItemToInventoried = Pick<IInventaryItem, 'inventario' | 'inventoried' | 'observations' | 'ubicacion' | 'edificio' | 'salon'>;

export interface IBusquedaGeneralResult {
    inventario: string;
    ubicacion: string | null;
    recibido_por: string | null;
    escuela: string | null;
    foto: string | null;
    foto_url: string | null;
  }
  