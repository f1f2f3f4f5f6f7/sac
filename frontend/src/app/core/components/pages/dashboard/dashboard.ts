import { Component, OnInit, ViewChild } from '@angular/core';
import { MessageService } from 'primeng/api';
import { FileUpload, FileUploadHandlerEvent, FileUploadModule } from 'primeng/fileupload';
import { InventaryService } from '../../../services/inventary/inventary.service';
import { Table, TableModule } from 'primeng/table';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { IInventaryItem } from '../../../models/inventary.model';
import { ToastModule } from 'primeng/toast';
import { BarcodeReader } from '../../../utils/barcode-reader/barcode-reader';
import { FormsModule } from '@angular/forms';
import { DialogModule } from 'primeng/dialog';
import { SelectButtonModule } from 'primeng/selectbutton';
import { MessageModule } from 'primeng/message';
import { FILEEVENTUPLOAD } from '../../../models/fileEvent.model';

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
  ],
  standalone: true,
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  providers: [MessageService],
})
export class Dashboard implements OnInit {
  uploadedFiles: any[] = [];
  inventario: any[] = [];
  selectedItem!: IInventaryItem[] | null;
  @ViewChild('dt') dt!: Table;
  globalQuery: string = '';
  visible: boolean = false;
  category!: string;
  private eventFileUpload: FILEEVENTUPLOAD | null = null;
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
    this.inventaryServices.inventary$.subscribe((data) => {
      this.inventario = data;
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
    this.inventaryServices.uploadFile(this.uploadedFiles[0], this.category).subscribe({
      next: (res: any) => {
        console.log(res);
        this.messageService.add({
          severity: 'info',
          summary: 'Archivo Cargado',
          detail: '',
        });
        fileForm.clear();
        this.uploadedFiles = [];
        this.inventario = [...res.nuevos, ...this.inventario];
      },
      error: (err) => {
        console.log(err);
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
    throw new Error('Method not implemented.');
  }
}
