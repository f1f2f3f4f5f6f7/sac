import { Component, inject, OnInit } from '@angular/core';
import { NotificationsService } from '../../../services/notifications/notifications.service';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { CommonModule } from '@angular/common';
import { ConfirmDialog } from 'primeng/confirmdialog';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { parseDate } from '../../../utils/parseDate';
import { FileUpload, FileUploadHandlerEvent } from 'primeng/fileupload';
import { ConfirmationService, MessageService } from 'primeng/api';
import { FormalitiesService } from '../../../services/formalities/formalities.service';

@Component({
  selector: 'app-notifications',
  imports: [
    CardModule,
    DialogModule,
    ButtonModule,
    CommonModule,
    FileUpload,
    ConfirmDialog,
    TagModule,
    ToastModule
  ],
  standalone: true,
  templateUrl: './notifications.html',
  styleUrl: './notifications.scss',
  providers: [ConfirmationService, MessageService],
})
export class Notifications implements OnInit {
  private notifcationService = inject(NotificationsService);
  private confirmationService = inject(ConfirmationService);
  private formalitiesService = inject(FormalitiesService);
  private messageService = inject(MessageService);

  uploadedFiles: any[] = [];
  selectedNotification: any = null;
  visible: boolean = false;
  parseDate = parseDate;

  notifications: any[] = [];

  ngOnInit(): void {
    this.notifcationService.getNotificactions().subscribe((data) => {
      this.notifications = data;
    });
  }

  selectNotification(notification: any) {
    this.visible = true;
    this.selectedNotification = notification;
  }

  onUpload(event: FileUploadHandlerEvent, fileForm: FileUpload) {
    for (const file of event.files) {
      this.uploadedFiles.push(file);
    }
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
    const meta = this.selectedNotification?.meta || {};
    const body = {
      archivo: meta.archivo_generado || '',
      accion: accion,
      tramite: 'confirmar_cancelar_traslado',
    };
    this.formalitiesService.confirmTramitePending(this.uploadedFiles[0], body).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Trámite completado',
        });
        this.visible = false;
        this.notifications = this.notifications.map((n) =>
          n.id === this.selectedNotification?.id ? { ...n, leida: true } : n,
        );

        this.selectedNotification = undefined;
        this.uploadedFiles = [];
      },
      error: (err) => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: err.error || 'Error al completar el trámite',
        });
      },
    });
  }

  isRead(leida: boolean): string {
    return leida ? 'Leída' : 'No leída';
  }

  getSeverity(leida: boolean) {
    return leida ? 'success' : 'danger';
  }
}
