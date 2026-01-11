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
import { DialogModule } from 'primeng/dialog';
import { BarcodeReader } from '../../../utils/barcode-reader/barcode-reader';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MessageModule } from 'primeng/message';
import { ToastModule } from 'primeng/toast';
import { TextareaModule } from 'primeng/textarea';
import { InputNumber } from 'primeng/inputnumber';
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
    ProgressSpinnerModule,
    DialogModule,
    MessageModule,
    ToastModule,
    TextareaModule,
    InputNumber,
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

    this.buildingService.buildings$
      .pipe(
        takeUntil(this.$destroy),
        switchMap((data) => {
          if (data.length === 0) {
            return this.buildingService.getBuildings();
          }
          return of(data);
        })
      )
      .subscribe({
        next: (data: any) => {
          this.edificios = data.map((building: any) => ({
            name: building.edificio,
            value: building.id,
          }));
        },
        error: () => {
          this.errorMessage('Error al cargar los edificios');
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

  async onShowDialog() {
    this.video = document.getElementById('video') as HTMLVideoElement;
    this.canvas = document.getElementById('canvas') as HTMLCanvasElement;
    this.button = document.getElementById('startbutton') as HTMLButtonElement;
    this.photo = document.querySelector('.photo') as HTMLImageElement;
    this.video.style.height = '0';
    await this.videoStream();
  }

  async videoStream() {
    this.retake = false;
    this.canvas.style.display = 'none';
    this.video.style.display = 'flex';
    const constraints = {
      video: { facingMode: 'environment', width: 640, height: 480 },
      audio: false,
    };
    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = stream;
      this.video.play();
      this.video.style.height = '383px';
      this.cameraStarted = true;
    } catch (error) {
      console.log('⚠️ No se pudo iniciar la cámara:', error);
    }
  }

  takePhoto() {
    this.retake = true;
    this.video.style.display = 'none';
    this.canvas.style.display = 'flex';
    this.canvas.width = this.video.videoWidth;
    this.canvas.height = this.video.videoHeight;
    const context = this.canvas.getContext('2d');
    context?.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
    const dataUrl = this.canvas.toDataURL('image/png');
    this.photo.setAttribute('src', dataUrl);
  }

  closeDialog() {
    this.visible = false;

    const stream = this.video.srcObject as MediaStream | null;

    if (stream) {
      const tracks = stream.getTracks();
      tracks.forEach((track) => track.stop());
    }

    this.video.srcObject = null;
    this.video.pause();
  }

  async onSubmit(form: NgForm) {
    if (form.valid && this.retake) {
      const file = await this.canvasToFile(this.canvas);
      const inventario = this.selectedItem?.inventario || '';
      const inventaryObject: IInvetaryItemToInventoried = {
        inventario: inventario,
        inventoried: true,
        observations: this.observations,
        ubicacion: this.selectedBuilding.value,
        salon: this.salon?.toString() || '',
      };
      this.closeDialog();
      this.inventaryServices.updateItem(inventaryObject, file).subscribe({
        next: (res: any) => {
          this.inventario = this.inventario.map((item) => {
            if (item.inventario !== inventario) return item;
            console.log(inventaryObject);
            
            return {
              ...item,
              inventoried: true,
              observations: inventaryObject.observations,
              ubicacion: this.getUbicationName(inventaryObject.ubicacion),
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
          console.log(this.inventario);
        },
        error: (err) => this.errorMessage('Error al actualizar el inventario'),
      });

      form.resetForm();
    }
  }

  canvasToFile(canvas: HTMLCanvasElement): Promise<File> {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject('No se pudo generar el blob');
          return;
        }
        const file = new File([blob], 'foto.png', { type: 'image/png' });
        resolve(file);
      }, 'image/png');
    });
  }

  ngOnDestroy(): void {
    this.$destroy.next();
    this.$destroy.complete();
  }

  getUbicationName(id: number){
    const building = this.edificios.find(b => b.value === id);
    return building ? building.name : 'Desconocido';
  }

  errorMessage(message: string) {
    this.messageService.add({
      severity: 'error',
      summary: 'Error',
      detail: message,
    });
  }
}
