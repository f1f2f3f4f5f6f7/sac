import { Component, OnInit, ViewChild } from '@angular/core';
import { MessageService } from 'primeng/api';
import { FileUploadModule } from 'primeng/fileupload';
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
    FormsModule
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

  onUpload(event: any, fileForm: any) {
    for (const file of event.files) {
      this.uploadedFiles.push(file);
    }
    console.log(event);

    console.log(this.uploadedFiles);
    this.inventaryServices.uploadFile(this.uploadedFiles[0]).subscribe({
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
    console.log(message);
    this.globalQuery = message; // Muestra el valor en el input
    this.dt.filterGlobal(message, 'contains'); // Aplica el filtro directamente
  }

  deleteItem(item: IInventaryItem) {
    throw new Error('Method not implemented.');
  }
  editItem(item: IInventaryItem) {
    throw new Error('Method not implemented.');
  }
}
