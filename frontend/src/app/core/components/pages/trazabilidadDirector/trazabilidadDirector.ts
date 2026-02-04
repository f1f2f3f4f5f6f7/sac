import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Subject, takeUntil, switchMap, of, tap, map } from 'rxjs';

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
import { InputTextModule } from 'primeng/inputtext';

import { UsersService } from '../../../services/users/users.service';
import { UserFromBackend } from '../../../models/user.model';

interface TrazabilidadItemDirector {
  id: number;
  fecha: string;
  accion: string;
  detalle: string | null;
  inventario: string | null;
  meta: any;
  usuario_id: number;
  usuario_nombre: string;
}

interface HistorialDirectorResponse {
  usuario_id: number;
  usuario_nombre: string;
  total_registros: number;
  resultados: TrazabilidadItemDirector[];
}

interface SelectOption {
  name: string;
  code: string | number | null;
}

@Component({
  selector: 'app-trazabilidad-director',
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
    InputTextModule,
  ],
  templateUrl: './trazabilidadDirector.html',
  styleUrl: './trazabilidadDirector.scss',
})
export class TrazabilidadDirector implements OnInit {
  private http = inject(HttpClient);
  private userService = inject(UsersService);
  private readonly baseUrl = 'http://localhost:8000';
  private $destroy = new Subject<void>();

  // Usuario seleccionado
  usuarios: UserFromBackend[] = [];
  selectedUsuario: UserFromBackend | null = null;
  usuarioSeleccionado = false;

  // Datos
  movimientos: TrazabilidadItemDirector[] = [];
  usuarioConsultado: { id: number; nombre: string } | null = null;

  // Estado UI
  loading = false;
  error: string | null = null;

  // Filtros
  tipoOptions: SelectOption[] = [];
  anioOptions: SelectOption[] = [];
  mesOptions: SelectOption[] = [];

  selectedTipo: SelectOption | null = null;
  selectedAnio: SelectOption | null = null;
  selectedMes: SelectOption | null = null;

  // Filtro local por número de inventario
  inventarioFilter: string = '';

  ngOnInit(): void {
    this.initFilters();
    this.loadUsuarios();
  }

  private loadUsuarios() {
    this.userService.users$
      .pipe(
        takeUntil(this.$destroy),
        switchMap((data: UserFromBackend[]) => {
          if (data.length === 0) {
            return this.userService.getUsers().pipe(
              tap((response) => {
                if (response.success) {
                  this.userService.users = response.users;
                }
              }),
              map((response) => response.users)  // <- ahora devolvemos UserFromBackend[]
            );
          }
          return of(data); // <- también UserFromBackend[]
        }),
      )
      .subscribe({
        next: (users: UserFromBackend[]) => {
          this.usuarios = users;
        },
        error: () => {
          this.error = 'Error al cargar la lista de usuarios.';
        },
      });
  }

  private initFilters() {
    this.tipoOptions = [
      { name: 'Todos', code: null },
      { name: 'Baja', code: 'baja' },
      { name: 'Préstamo', code: 'prestamo' },
      { name: 'Traslado', code: 'traslado' },
    ];

    const currentYear = new Date().getFullYear();
    const yearsRange = 5;
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
    this.selectedAnio = this.anioOptions[0];
    this.selectedMes = this.mesOptions[0];
  }

  onUsuarioSelected() {
    if (this.selectedUsuario) {
      this.usuarioSeleccionado = true;
      this.usuarioConsultado = null;
      this.movimientos = [];
      this.error = null;
      this.loadTrazabilidad();
    } else {
      this.usuarioSeleccionado = false;
      this.movimientos = [];
      this.usuarioConsultado = null;
    }
  }

  loadTrazabilidad() {
    if (!this.selectedUsuario) {
      this.error = 'Debes seleccionar un usuario primero.';
      return;
    }

    this.loading = true;
    this.error = null;

    let params = new HttpParams();

    // Parámetro obligatorio: usuario_id o usuario_nombre
    params = params.set('usuario_id', String(this.selectedUsuario.id));

    // Filtros opcionales
    const tipo = this.selectedTipo?.code;
    const anio = this.selectedAnio?.code;
    const mes = this.selectedMes?.code;

    if (tipo) {
      params = params.set('tipo', String(tipo));
    }
    if (anio) {
      params = params.set('year', String(anio));
    }
    if (mes && anio) {
      params = params.set('month', String(mes));
    }

    const endpoint = `${this.baseUrl}/api/movimientos/consultar_trazabilidad_usuario/`;

    this.http.get<HistorialDirectorResponse>(endpoint, { params }).subscribe({
      next: (resp) => {
        this.movimientos = resp.resultados ?? [];
        this.usuarioConsultado = {
          id: resp.usuario_id,
          nombre: resp.usuario_nombre,
        };
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
    this.selectedAnio = this.anioOptions[0];
    this.selectedMes = this.mesOptions[0];
    this.inventarioFilter = '';
    if (this.usuarioSeleccionado) {
      this.loadTrazabilidad();
    }
  }

  resetUsuario() {
    this.selectedUsuario = null;
    this.usuarioSeleccionado = false;
    this.movimientos = [];
    this.usuarioConsultado = null;
    this.error = null;
    this.inventarioFilter = '';
  }

  getAccionSeverity(accion: string | null | undefined): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
    const value = (accion || '').toLowerCase();
    if (value === 'baja') return 'danger';
    if (value === 'prestamo') return 'info';
    if (value === 'traslado') return 'warn';
    return 'secondary';
  }

  formatFecha(fechaIso: string): string {
    if (!fechaIso) return '';
    const d = new Date(fechaIso);
    if (isNaN(d.getTime())) return fechaIso;
    return d.toLocaleString();
  }

  detalleCorto(detalle: string | null | undefined, max: number = 80): string {
    if (!detalle) return '';
    if (detalle.length <= max) return detalle;
    return detalle.slice(0, max) + '...';
  }

  get movimientosFiltrados(): TrazabilidadItemDirector[] {
    if (!this.inventarioFilter?.trim()) {
      return this.movimientos;
    }

    const term = this.inventarioFilter.trim().toLowerCase();

    return this.movimientos.filter((m) =>
      (m.inventario || '').toLowerCase().includes(term),
    );
  }

  ngOnDestroy(): void {
    this.$destroy.next();
    this.$destroy.complete();
  }
}