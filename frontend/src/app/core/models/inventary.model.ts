export interface IInventaryItem {
  categoria: string;
  descripcion: string;
  entregado_por: string;
  escuela: string;
  serial: string;
  fecha_recibido: string;
  inventario: string;
  inventoried: boolean;
  marca: string;
  recibido_por: string;
  ubicacion: string;
  observations: string;
  edificio?: string;
  salon: string;
  valor: number;
  foto: string;
  imagen_url: string | null;
}

export type IInvetaryItemToInventoried = Pick<
  IInventaryItem,
  'inventario' | 'inventoried' | 'observations' | 'ubicacion' | 'edificio' | 'salon'
>;

export interface IInventaryWriteOff {
  items: IItemWriteOff[]
}

export interface IItemWriteOff {
  inventario: string;
  motivo: string;
  imagen_url?: string | null;
}

export type IInventaryLoan = {
  fecha_devolucion: string;
  nombre_solicitante: string;
  unidad_entidad: string;
  nombre_proyecto: string;
  justificacion: string;
  items: IInventaryLoanInventary[];
};

export type IInvetaryTransfer = {
  destinatario_nombre: string
  items: IItemWriteOff[];
}

export type IInventaryLoanInventary = Pick<IInventaryItem, 'inventario'>;

export interface IBusquedaGeneralResult {
  inventario: string;
  ubicacion: string | null;
  recibido_por: string | null;
  escuela: string | null;
  foto: string | null;
  foto_url: string | null;
}
