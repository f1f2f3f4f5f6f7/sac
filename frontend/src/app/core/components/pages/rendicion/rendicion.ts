import { Component, input, OnDestroy, OnInit, ViewChild, viewChild } from '@angular/core';
import { MessageService, SelectItem } from 'primeng/api';
import { InventaryService } from '../../../services/inventary/inventary.service';
import { of, Subject, switchMap, takeUntil, tap } from 'rxjs';
import { IInventaryItem, IInvetaryItemToInventoried } from '../../../models/inventary.model';
import { DataView } from 'primeng/dataview';
import { ButtonModule } from 'primeng/button';
import { SelectModule } from 'primeng/select';
import { InputTextModule } from 'primeng/inputtext';
import { FormsModule, NgForm } from '@angular/forms';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { CommonModule } from '@angular/common';
import { TagModule } from 'primeng/tag';
import { ImageModule } from 'primeng/image';
import { BarcodeReader } from '../../../utils/barcode-reader/barcode-reader';
import { EditItem } from '../../../utils/edit-item/edit-item';
import { MessageModule } from 'primeng/message';
import { ToastModule } from 'primeng/toast';
import { IBuilding } from '../../../models/buildingModel';
import { BuildingService } from '../../../services/buildings/building.service';

@Component({
  selector: 'app-rendicion',
  imports: [
    DataView,
    ButtonModule,
    SelectModule,
    InputTextModule,
    FormsModule,
    CommonModule,
    IconFieldModule,
    InputIconModule,
    BarcodeReader,
    TagModule,
    ImageModule,
    MessageModule,
    ToastModule,
    EditItem,
  ],
  templateUrl: './rendicion.html',
  styleUrl: './rendicion.scss',
  providers: [MessageService],
  standalone: true,
})
export class Rendicion implements OnInit, OnDestroy {
  selectedBuilding!: IBuilding;

  edificios: any[] = [
    {
      name: 'Edificio A',
      value: 'edificio_a',
    },
  ];

  inventario: IInventaryItem[] = [];
  selectedItem!: IInventaryItem | null;
  visible: boolean = false;
  sortOptions!: SelectItem[];
  sortOrder!: number;
  sortField!: string;
  retake: boolean = false;
  observations!: string;
  salon: number | undefined;

  @ViewChild('dv') dv!: DataView;

  video!: HTMLVideoElement;
  canvas!: HTMLCanvasElement;
  button!: HTMLButtonElement;
  photo!: HTMLImageElement;

  private $destroy = new Subject<void>();
  sortKey: any;
  globalQuery: string = '';

  cameraStarted: boolean = false;

  constructor(
    private messageService: MessageService,
    private inventaryServices: InventaryService,
    private buildingService: BuildingService
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
        },
        error: () => {
          this.errorMessage('Error al cargar el inventario');
        },
      });

    this.sortOptions = [
      { label: 'Inventariados', value: true },
      { label: 'No inventariados', value: false },
    ];
  }

  onSortChange(e: any) {
    this.sortField = 'inventoried';
    this.sortOrder = e.value === true ? -1 : 1;
  }

  getBarcodeNumber(message: string) {
    this.globalQuery = message;
    this.dv.filter(message);
  }

  getSeverity(item: IInventaryItem) {
    const inventoried = item.inventoried;
    return inventoried ? 'success' : 'danger';
  }

  returnSeveriryLabel(item: IInventaryItem) {
    return item ? 'Inventariado' : 'No inventariado';
  }

  openInventaryDialog(item: IInventaryItem) {
    this.visible = true;
    this.selectedItem = item;
  }

  closeDialog() {
    this.visible = false;
  }

  submitItem($event: { inventaryObject: IInvetaryItemToInventoried; file: File }) {
    const { inventaryObject, file } = $event;
    const inventario = inventaryObject.inventario
    this.inventaryServices.updateItem(inventaryObject, file).subscribe({
      next: (res: any) => {
        this.inventario = this.inventario.map((item) => {
          if (item.inventario !== inventario) return item;

          return {
            ...item,
            inventoried: true,
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

  ngOnDestroy(): void {
    this.$destroy.next();
    this.$destroy.complete();
  }

  getUbicationName(id: number) {
    const building = this.edificios.find((b) => b.value === id);
    return building ? building.name : 'Desconocido';
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
}
