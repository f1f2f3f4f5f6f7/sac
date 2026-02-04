import { Component, OnInit } from '@angular/core';
import { FormalitiesService } from '../../../services/formalities/formalities.service';
import { takeUntil, Subject } from 'rxjs';
import { MessageService } from 'primeng/api';
import { GroupedByArchivo } from '../../../models/tramites.model';
import { TableModule } from 'primeng/table';
import { CommonModule } from '@angular/common';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { TagModule } from 'primeng/tag';
import { BadgeModule } from 'primeng/badge';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { BaseIcon } from "primeng/icons/baseicon";

@Component({
  selector: 'app-tramites.pendientes',
  imports: [
    TableModule,
    CommonModule,
    DialogModule,
    IconFieldModule,
    InputIconModule,
    TagModule,
    BadgeModule,
    ButtonModule,
    CardModule,
],
  standalone: true,
  templateUrl: './tramites.pendientes.html',
  styleUrl: './tramites.pendientes.scss',
  providers: [MessageService],
})
export class TramitesPendientes implements OnInit {
  tramitesPending: GroupedByArchivo[] = [];
  private $destroy = new Subject<void>();
  selectedArchivo?: GroupedByArchivo;
  visible: boolean = false;

  constructor(
    private formalitiesService: FormalitiesService,
    private messageService: MessageService,
  ) {}

  ngOnInit(): void {
    this.formalitiesService
      .getTramitePending()
      .pipe(takeUntil(this.$destroy))
      .subscribe({
        next: (data: GroupedByArchivo[]) => {
          this.tramitesPending = tramitesMap(data);
          console.log(this.tramitesPending);
        },
        error: () => {
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Error al cargar los trámites pendientes',
          });
        },
      });

    const tramitesMap = (data: any[]): GroupedByArchivo[] => {
      const map = new Map<string, GroupedByArchivo>();

      for (const item of data) {
        const archivo = item.meta?.archivo || 'Sin archivo';
        if (!map.has(archivo)) {
          map.set(archivo, {
            archivo: archivo,
            ruta_archivo: item.meta?.ruta_archivo || '',
            accion: item.accion || '',
            fecha_tramite: item.fecha || '',
            items: [],
          });
        }
        map.get(archivo)!.items.push({
          accion: item.accion,
          descripcion_item: item.descripcion_item,
          numero_inventario: item.numero_inventario,
          detalle: item.detalle,
          estado: item.estado,
          fecha: item.fecha,
          usuario_id: item.usuario_id,
          meta: item.meta || {},
        });
      }

      return Array.from(map.values());
    };
  }

  getSeverity(accion: string) {
    switch (accion.toLowerCase()) {
      case 'traslado':
        return 'warn';
      case 'baja':
        return 'danger';
      case 'préstamo':
        return 'info';
      default:
        return 'success';
    }
  }

  selectArchivo(archivo: GroupedByArchivo) {
    this.selectedArchivo = archivo;
    console.log(this.selectedArchivo);
    this.visible = true;
  }

  onImageError(event: any) {
    event.target.src = 'http://localhost:8000/media/inventario_images/noimage.webp';
  }

  parseDate(dateString: string): string {
    const fecha = new Date(dateString);

    const dia = String(fecha.getUTCDate()).padStart(2, '0');
    const mes = String(fecha.getUTCMonth() + 1).padStart(2, '0'); // +1 porque empieza en 0
    const anio = fecha.getUTCFullYear();

    const resultado = `${dia}/${mes}/${anio}`;
    return resultado;
  }

  ngOnDestroy() {
    this.$destroy.next();
    this.$destroy.complete();
  }
}
