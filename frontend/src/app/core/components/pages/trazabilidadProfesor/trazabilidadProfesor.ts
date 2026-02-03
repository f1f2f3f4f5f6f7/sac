import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';

/* PrimeNG */
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { SelectModule } from 'primeng/select';
import { ButtonModule } from 'primeng/button';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { MessageModule } from 'primeng/message';
import { TooltipModule } from 'primeng/tooltip';
import { FloatLabelModule } from 'primeng/floatlabel';
import { InputGroupModule } from 'primeng/inputgroup';
import { InputTextModule } from 'primeng/inputtext';



interface TrazabilidadItem {
  id: number;
  inventario_id: number;
  numero_inventario: string | null;
  descripcion_item: string | null;
  fecha: string; // ISO string desde el backend
  accion: string;
  estado: string | null;
  detalle: string | null;
  usuario_id: number;
  meta: any;
}

interface HistorialResponse {
  filtros_aplicados: {
    tipo: string | null;
    anio: number | null;
    mes: number | null;
    estado: string | null;
  };
  total: number;
  resultados: TrazabilidadItem[];
}

interface SelectOption {
  name: string;
  code: string | number | null;
}

@Component({
  selector: 'app-trazabilidad-profesor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    TableModule,
    TagModule,
    SelectModule,
    ButtonModule,
    IconFieldModule,
    InputIconModule,
    MessageModule,
    TooltipModule,
    FloatLabelModule,
    InputGroupModule,
    InputTextModule,
  ],
  templateUrl: './trazabilidadProfesor.html',
  styleUrl: './trazabilidadProfesor.scss',
})
export class TrazabilidadProfesor implements OnInit {
  private http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  // Datos
  movimientos: TrazabilidadItem[] = [];

  // Estado UI
  loading = false;
  error: string | null = null;

  // Filtros
  tipoOptions: SelectOption[] = [];
  estadoOptions: SelectOption[] = [];
  anioOptions: SelectOption[] = [];
  mesOptions: SelectOption[] = [];

  selectedTipo: SelectOption | null = null;
  selectedEstado: SelectOption | null = null;
  selectedAnio: SelectOption | null = null;
  selectedMes: SelectOption | null = null;

  // Filtro local por número de inventario
  inventarioFilter: string = '';

  ngOnInit(): void {
    this.initFilters();
    this.loadTrazabilidad(); // carga inicial sin filtros
  }

  private initFilters() {
    this.tipoOptions = [
      { name: 'Todos', code: null },
      { name: 'Baja', code: 'baja' },
      { name: 'Préstamo', code: 'Prestamo' },
      { name: 'Traslado', code: 'traslado' },
    ];

    this.estadoOptions = [
      { name: 'Todos', code: null },
      { name: 'Pendiente', code: 'pendiente' },
      { name: 'Completado', code: 'completado' },
    ];

    const currentYear = new Date().getFullYear();
    const yearsRange = 5; // últimos 5 años
    this.anioOptions = [{ name: 'Todos', code: null }];
    for (let y = 0; y < yearsRange; y++) {
      const year = currentYear - y;
      this.anioOptions.push({ name: year.toString(), code: year });
    }

    this.mesOptions = [
      { name: 'Todos', code: null },
      { name: 'Enero', code: 1 },
      { name: 'Febrero', code: 2 },
      { name: 'Marzo', code: 3 },
      { name: 'Abril', code: 4 },
      { name: 'Mayo', code: 5 },
      { name: 'Junio', code: 6 },
      { name: 'Julio', code: 7 },
      { name: 'Agosto', code: 8 },
      { name: 'Septiembre', code: 9 },
      { name: 'Octubre', code: 10 },
      { name: 'Noviembre', code: 11 },
      { name: 'Diciembre', code: 12 },
    ];

    this.selectedTipo = this.tipoOptions[0];
    this.selectedEstado = this.estadoOptions[0];
    this.selectedAnio = this.anioOptions[0];
    this.selectedMes = this.mesOptions[0];
  }

  loadTrazabilidad() {
    this.loading = true;
    this.error = null;

    let params = new HttpParams();

    const tipo = this.selectedTipo?.code;
    const estado = this.selectedEstado?.code;
    const anio = this.selectedAnio?.code;
    const mes = this.selectedMes?.code;

    if (tipo) {
      params = params.set('tipo', String(tipo));
    }
    if (estado) {
      params = params.set('estado', String(estado));
    }
    if (anio) {
      params = params.set('anio', String(anio));
    }
    if (mes && anio) {
      // el backend exige año cuando hay mes
      params = params.set('mes', String(mes));
    }

    const endpoint = `${this.baseUrl}/api/movimientos/consultar_trazabilidad/`;

    this.http.get<HistorialResponse>(endpoint, { params }).subscribe({
      next: (resp) => {
        this.movimientos = resp.resultados ?? [];
        this.loading = false;
      },
      error: (err) => {
        const backendMessage =
          err?.error?.error || err?.error?.detail || err?.message || 'Error al cargar la trazabilidad.';
        this.error = backendMessage;
        this.movimientos = [];
        this.loading = false;
      },
    });
  }

  clearFilters() {
    this.selectedTipo = this.tipoOptions[0];
    this.selectedEstado = this.estadoOptions[0];
    this.selectedAnio = this.anioOptions[0];
    this.selectedMes = this.mesOptions[0];
    this.loadTrazabilidad();
  }

  getAccionSeverity(accion: string | null | undefined): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
    const value = (accion || '').toLowerCase();
    if (value === 'baja') return 'danger';
    if (value === 'prestamo') return 'info';
    if (value === 'traslado') return 'warn';
    return 'secondary';
  }

  getEstadoSeverity(estado: string | null | undefined): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
    const value = (estado || '').toLowerCase();
    if (value === 'pendiente') return 'warn';
    if (value === 'completado') return 'success';
    return 'secondary';
  }

  formatFecha(fechaIso: string): string {
    if (!fechaIso) return '';
    const d = new Date(fechaIso);
    if (isNaN(d.getTime())) return fechaIso;
    return d.toLocaleString(); // fecha + hora en locale
  }

  detalleCorto(detalle: string | null | undefined, max: number = 80): string {
    if (!detalle) return '';
    if (detalle.length <= max) return detalle;
    return detalle.slice(0, max) + '...';
  }


  get movimientosFiltrados(): TrazabilidadItem[] {
    if (!this.inventarioFilter?.trim()) {
      return this.movimientos;
    }
  
    const term = this.inventarioFilter.trim().toLowerCase();
  
    return this.movimientos.filter((m) =>
      (m.numero_inventario || '').toLowerCase().includes(term),
    );
  }
}