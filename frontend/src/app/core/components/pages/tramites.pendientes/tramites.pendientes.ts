import { Component, OnInit } from '@angular/core';
import { FormalitiesService } from '../../../services/formalities/formalities.service';
import { takeUntil, Subject } from 'rxjs';
import { ConfirmationService, MessageService } from 'primeng/api';
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
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { FileUpload, FileUploadHandlerEvent, FileUploadModule } from 'primeng/fileupload';
import { ToastModule } from 'primeng/toast';
import { parseDate } from '../../../utils/parseDate';

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
    ConfirmDialogModule,
    FileUploadModule,
    ToastModule,
  ],
  standalone: true,
  templateUrl: './tramites.pendientes.html',
  styleUrl: './tramites.pendientes.scss',
  providers: [MessageService, ConfirmationService],
})
export class TramitesPendientes implements OnInit {
  tramitesPending: GroupedByArchivo[] = [];
  private $destroy = new Subject<void>();
  selectedArchivo?: GroupedByArchivo;
  visible: boolean = false;
  uploadedFiles: any[] = [];
  parseDate = parseDate;

  constructor(
    private formalitiesService: FormalitiesService,
    private messageService: MessageService,
    private confirmationService: ConfirmationService,
  ) {}

  ngOnInit(): void {
    this.formalitiesService
      .getTramitePending()
      .pipe(takeUntil(this.$destroy))
      .subscribe({
        next: (data: GroupedByArchivo[]) => {
          this.tramitesPending = tramitesMap(data);
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
    this.visible = true;
  }

  onImageError(event: any) {
    event.target.src = 'http://localhost:8000/media/inventario_images/noimage.webp';
  }


  denied(event: Event) {
    this.confirmationService.confirm({
      target: event.currentTarget as EventTarget,
      modal: true,
      message: '¿Deseas confirmar la denegación de este trámite?',
      icon: 'pi pi-info-circle',
      acceptLabel: 'Sí, denegar',
      rejectLabel: 'No, cancelar',
      rejectButtonProps: {
        label: 'Cancel',
        severity: 'secondary',
        outlined: true,
      },
      acceptButtonProps: {
        label: 'Denegar',
        severity: 'danger',
      },
      accept: () => {
        this._confirmTramite('cancelar');
      },
      closable: false,
    });
  }

  approved(event: Event) {
    this.confirmationService.confirm({
      target: event.currentTarget as EventTarget,
      modal: true,
      message: '¿Deseas confirmar la aprobación de este trámite?',
      icon: 'pi pi-info-circle',
      acceptLabel: 'Sí, aprobar',
      rejectLabel: 'No, cancelar',
      rejectButtonProps: {
        label: 'Cancel',
        severity: 'secondary',
        outlined: true,
      },
      acceptButtonProps: {
        label: 'Aprobar',
        severity: 'success',
      },
      accept: () => {
        this._confirmTramite('confirmar');
      },
      closable: false,
    });
  }

  _confirmTramite(accion: string) {
    const body = {
      archivo: this.selectedArchivo?.archivo || '',
      accion: accion,
      tramite: this.getActionLabel(this.selectedArchivo?.accion || ''),
    };
    this.formalitiesService.confirmTramitePending(this.uploadedFiles[0], body).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Trámite completado',
        });
        this.visible = false;
        this.tramitesPending = this.tramitesPending.filter(
          (t) => t.archivo !== this.selectedArchivo?.archivo,
        );
        this.selectedArchivo = undefined;
        this.uploadedFiles = [];
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Error al completar el trámite',
        });
      },
    });
  }

  onUpload(event: FileUploadHandlerEvent, fileForm: FileUpload) {
    for (const file of event.files) {
      this.uploadedFiles.push(file);
    }
  }

  getActionLabel(accion: string): string {
    switch (accion.toLowerCase()) {
      case 'traslado':
        return 'confirmar_cancelar_traslado';
      case 'baja':
        return 'confirmar_cancelar_baja';
      case 'prestamo':
        return 'confirmar_cancelar_prestamo';
      default:
        return 'Acción desconocida';
    }
  }

  ngOnDestroy() {
    this.$destroy.next();
    this.$destroy.complete();
  }
}
