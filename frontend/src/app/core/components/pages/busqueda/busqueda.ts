import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { BarcodeReader } from '../../../utils/barcode-reader/barcode-reader';
import { Subject, takeUntil } from 'rxjs';
import { IBusquedaGeneralResult } from '../../../models/inventary.model';
import { InventaryService } from '../../../services/inventary/inventary.service';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { ImageModule } from 'primeng/image';
import { MessageModule } from 'primeng/message';
import { CardModule } from 'primeng/card';
import { PanelModule } from 'primeng/panel';
import { DividerModule } from 'primeng/divider';


@Component({
  selector: 'app-busqueda',
  standalone: true,
  templateUrl: './busqueda.html',
  styleUrl: './busqueda.scss',
  imports: [
    CommonModule, 
    FormsModule, 
    InputTextModule,
    ButtonModule,  // Agregar ButtonModule
    TableModule,
    BarcodeReader, 
    ToastModule, 
    ProgressSpinnerModule,
    ImageModule, 
    MessageModule, 
    CardModule, 
    PanelModule, 
    DividerModule
  ],
  providers: [MessageService],
})
export class Busqueda implements OnInit, OnDestroy {
  globalQuery = '';
  resultado: IBusquedaGeneralResult | null = null;
  loading = false;
  error: string | null = null;

  private $destroy = new Subject<void>();

  constructor(
    private inventaryService: InventaryService,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
    // Ya no necesitamos el debounce, la búsqueda será por botón
  }

  // Método público para buscar (llamado desde el botón o Enter)
  buscar() {
    if (!this.globalQuery?.trim()) {
      this.resultado = null;
      this.error = null;
      return;
    }
    this.buscarInventario(this.globalQuery);
  }

  // Evento desde el lector de códigos
  getBarcodeNumber(value: string) {
    this.globalQuery = value;
    this.buscarInventario(value);
  }

  // Lógica de búsqueda en el backend
  private buscarInventario(inventarioNumero: string) {
    const query = inventarioNumero?.trim();
    
    if (!query) {
      this.resultado = null;
      this.error = null;
      return;
    }

    this.loading = true;
    this.error = null;
    this.resultado = null;

    this.inventaryService.buscarInventarioGeneral(query).subscribe({
      next: (item) => {
        this.resultado = item;
        this.loading = false;
        this.messageService.add({
          severity: 'success',
          summary: 'Encontrado',
          detail: `Inventario ${item.inventario} encontrado`,
        });
      },
      error: (err) => {
        this.loading = false;
        this.resultado = null;
        const errorMessage = err?.error?.message || err?.message || 'No se encontró el inventario';
        this.error = errorMessage;
        this.messageService.add({
          severity: 'warn',
          summary: 'No encontrado',
          detail: errorMessage,
        });
      },
    });
  }

  ngOnDestroy(): void {
    this.$destroy.next();
    this.$destroy.complete();
  }
}