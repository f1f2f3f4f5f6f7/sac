import { Component, OnDestroy, OnInit, ViewChild, viewChild } from '@angular/core';
import { MessageService, SelectItem } from 'primeng/api';
import { InventaryService } from '../../../services/inventary/inventary.service';
import { Subject, takeUntil } from 'rxjs';
import { IInventaryItem } from '../../../models/inventary.model';
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
  ],
  templateUrl: './rendicion.html',
  styleUrl: './rendicion.scss',
  providers: [MessageService],
  standalone: true,
})
export class Rendicion implements OnInit, OnDestroy {
  selectedBuilding!: object;
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
    private inventaryServices: InventaryService
  ) {}

  ngOnInit() {
    this.inventaryServices.inventary$.pipe(takeUntil(this.$destroy)).subscribe((data) => {
      this.inventario = data;
      this.inventario.forEach((item) => (item.inventoried = Math.random() < 0.5));
      console.log(data);
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

  onSubmit(form: NgForm) {
    console.log(form.valid);

    if (form.valid && this.retake) {
      console.log(this.selectedBuilding);
      this.canvas.toBlob((blob) => {
        if (!blob) {
          return;
        }
        const file = new File([blob], 'foto.png', { type: 'image/png' });
      }, 'image/png');
      form.resetForm();
    }
  }

  ngOnDestroy(): void {
    this.$destroy.next();
    this.$destroy.complete();
  }
}
