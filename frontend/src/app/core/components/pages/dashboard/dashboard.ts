import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { MessageService } from 'primeng/api';
import { FileUpload, FileUploadHandlerEvent, FileUploadModule } from 'primeng/fileupload';
import { InventaryService } from '../../../services/inventary/inventary.service';
import { Table, TableModule } from 'primeng/table';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { IInventaryItem, IInvetaryItemToInventoried } from '../../../models/inventary.model';
import { ToastModule } from 'primeng/toast';
import { BarcodeReader } from '../../../utils/barcode-reader/barcode-reader';
import { FormsModule } from '@angular/forms';
import { DialogModule } from 'primeng/dialog';
import { SelectButtonModule } from 'primeng/selectbutton';
import { MessageModule } from 'primeng/message';
import { FILEEVENTUPLOAD } from '../../../models/fileEvent.model';
import { of, Subject, switchMap, takeUntil, tap } from 'rxjs';
import { EditItem } from '../../../utils/edit-item/edit-item';

@Component({
  selector: 'app-dashboard',
  imports: [
    FileUploadModule,
    TableModule,
    IconFieldModule,
    InputIconModule,
    InputTextModule,
    ButtonModule,
    ToastModule,
    BarcodeReader,
    FormsModule,
    DialogModule,
    SelectButtonModule,
    MessageModule,
    EditItem,
  ],
  standalone: true,
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  providers: [MessageService],
})
export class Dashboard implements OnInit, OnDestroy {
  uploadedFiles: any[] = [];
  inventario: IInventaryItem[] = [];
  selectedItems: IInventaryItem[] = [];
  selectedItem!: IInventaryItem | null;
  @ViewChild('dt') dt!: Table;
  globalQuery: string = '';
  visible: boolean = false;
  category!: string;
  private eventFileUpload: FILEEVENTUPLOAD | null = null;
  private $destroy = new Subject<void>();
  categoryOptions: any[] = [
    { label: 'Mayores', value: 'Mayores' },
    { label: 'Menores', value: 'Menores' },
  ];

  inventaryItem: IInventaryItem | undefined;

  constructor(
    private messageService: MessageService,
    private inventaryServices: InventaryService
  ) {}

  ngOnInit() {
    this.inventaryServices.inventary$
      .pipe(
        takeUntil(this.$destroy),
        switchMap((data) => {
          if (data.length === 0) {
            return this.inventaryServices.getInventary().pipe(
              tap((data) => {
                this.inventaryServices.inventary = data;
              })
            );
          }
          return of(data);
        })
      )
      .subscribe({
        next: (data) => {
          this.inventario = data;
          console.log(this.inventario);
        },
        error: () => {
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Error al cargar el inventario',
          });
        },
      });
  }

  onSubmit(category: string) {
    this.category = category;
    this.visible = false;

    if (this.eventFileUpload) {
      const { originalEvent, fileForm } = this.eventFileUpload;
      this.eventFileUpload = null;
      this.onUpload(originalEvent, fileForm);
      this.category = '';
    }
  }

  onUpload(event: FileUploadHandlerEvent, fileForm: FileUpload) {
    if (!this.category) {
      this.eventFileUpload = { originalEvent: event, fileForm };
      this.visible = true;
      return;
    }
    for (const file of event.files) {
      this.uploadedFiles.push(file);
    }
    this.inventaryServices
      .uploadFile(this.uploadedFiles[0], this.category)
      .pipe(takeUntil(this.$destroy))
      .subscribe({
        next: (res: any) => {
          this.messageService.add({
            severity: 'info',
            summary: 'Archivo Cargado',
            detail: '',
          });
          fileForm.clear();
          this.uploadedFiles = [];
          this.inventario = [...res.inventarios_nuevos, ...this.inventario];
          this.inventaryServices.inventary = this.inventario;
        },
        error: (err) => {
          this.messageService.add({
            severity: 'error',
            summary: 'Fallo al cargar archivo',
            detail: err?.error?.error || 'Error al subir el archivo',
          });
          fileForm.clear();
          this.uploadedFiles = [];
        },
      });
  }

  getBarcodeNumber(message: string) {
    this.globalQuery = message;
    this.dt.filterGlobal(message, 'contains');
  }

  closeDialog() {
    this.visible = false;
    this.eventFileUpload = null;
    this.category = '';
  }

  deleteItem(item: IInventaryItem) {
    throw new Error('Method not implemented.');
  }
  editItem(item: IInventaryItem) {
    this.selectedItem = item;
    this.visible = true;
  }

  submitItem($event: { inventaryObject: IInvetaryItemToInventoried; file: File }) {
    const { inventaryObject, file } = $event;
    const inventario = inventaryObject.inventario;
    this.inventaryServices.updateItem(inventaryObject, file).subscribe({
      next: (res: any) => {
        this.inventario = this.inventario.map((item) => {
          if (item.inventario !== inventario) return item;

          return {
            ...item,
            observations: inventaryObject.observations,
            ubicacion: inventaryObject.edificio || item.ubicacion,
            salon: inventaryObject.salon,
            imagen_url: res.foto_url,
          };
        });
        this.messageService.add({
          severity: 'success',
          summary: 'Éxito',
          detail: 'Inventario actualizado correctamente',
        });
        this.inventaryServices.inventary = this.inventario;
      },
      error: (err) => this.errorMessage('Error al actualizar el inventario'),
    });
  }

  onImageError(event: any) {
    event.target.src = 'http://localhost:8000/media/inventario_images/noimage.webp';
  }

  errorMessage(message: string) {
    this.messageService.add({
      severity: 'error',
      summary: 'Error',
      detail: message,
    });
  }

  ngOnDestroy(): void {
    this.$destroy.next();
    this.$destroy.complete();
  }
}
