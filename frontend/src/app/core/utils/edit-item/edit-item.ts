import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { FormsModule, NgForm } from '@angular/forms';
import { IBuilding } from '../../models/buildingModel';
import { SelectModule } from 'primeng/select';
import { MessageModule } from 'primeng/message';
import { InputNumberModule } from 'primeng/inputnumber';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TextareaModule } from 'primeng/textarea';
import { IInventaryItem, IInvetaryItemToInventoried } from '../../models/inventary.model';
import { BuildingService } from '../../services/buildings/building.service';
import { of, Subject, switchMap, takeUntil } from 'rxjs';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-edit-item',
  imports: [
    CommonModule,
    DialogModule,
    ButtonModule,
    FormsModule,
    SelectModule,
    MessageModule,
    InputNumberModule,
    ProgressSpinnerModule,
    TextareaModule,
  ],
  standalone: true,
  templateUrl: './edit-item.html',
  styleUrl: './edit-item.scss',
})
export class EditItem {
  @Input() visible = false;
  @Input() selectedItem!: IInventaryItem | null;
  @Output() hideModal = new EventEmitter<boolean>();
  @Output() submitItem = new EventEmitter<{
    inventaryObject: IInvetaryItemToInventoried;
    file: File;
  }>();
  retake: boolean = false;
  cameraStarted: boolean = false;
  selectedBuilding!: IBuilding;
  salon: number | undefined;
  observations!: string;

  edificios: any[] = [
    {
      name: 'Edificio A',
      value: 'edificio_a',
    },
  ];

  video!: HTMLVideoElement;
  canvas!: HTMLCanvasElement;
  button!: HTMLButtonElement;
  photo!: HTMLImageElement;

  private $destroy = new Subject<void>();

  constructor(private buildingService: BuildingService, private messageService: MessageService) {}

  ngOnInit() {
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
    this.hideModal.emit(this.visible);

    const stream = this.video.srcObject as MediaStream | null;

    if (stream) {
      const tracks = stream.getTracks();
      tracks.forEach((track) => track.stop());
    }

    this.video.srcObject = null;
    this.video.pause();
  }

  errorMessage(message: string) {
    this.messageService.add({
      severity: 'error',
      summary: 'Error',
      detail: message,
    });
  }

  async onSubmit(form: NgForm) {
    if (form.valid && this.retake) {
      const file = await this.canvasToFile(this.canvas);
      const inventario = this.selectedItem?.inventario || '';
      const inventaryObject: IInvetaryItemToInventoried = {
        inventario: inventario,
        inventoried: true,
        observations: this.observations,
        ubicacion: (this.selectedBuilding.value).toString(),
        salon: this.salon?.toString() || '',
        edificio: this.getUbicationName(this.selectedBuilding.value),
      };
      this.closeDialog();
      this.submitItem.emit({ inventaryObject, file });
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

  getUbicationName(id: number) {
    const building = this.edificios.find((b) => b.value === id);
    return building ? building.name : 'Desconocido';
  }
}
