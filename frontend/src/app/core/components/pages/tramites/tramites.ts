import { Component, ViewChild } from '@angular/core';
import { MessageService } from 'primeng/api';
import { takeUntil, switchMap, tap, of, Subject } from 'rxjs';
import { InventaryService } from '../../../services/inventary/inventary.service';
import {
  IInventaryItem,
  IInventaryLoan,
  IInventaryLoanInventary,
  IInventaryWriteOff,
} from '../../../models/inventary.model';
import { MessageModule } from 'primeng/message';
import { Table, TableModule } from 'primeng/table';
import { CardModule } from 'primeng/card';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { BarcodeReader } from '../../../utils/barcode-reader/barcode-reader';
import { FormsModule } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { BadgeModule } from 'primeng/badge';
import { StepperModule } from 'primeng/stepper';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { ReactiveFormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { FloatLabel } from 'primeng/floatlabel';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { FormalitiesService } from '../../../services/formalities/formalities.service';
import { downLoadExcel } from '../../../utils/downloadExcel';
import { nameCode } from '../../../utils/nameCode.model';
import { ISchool } from '../../../models/school.model';
import { UserFromBackend } from '../../../models/user.model';
import { UsersService } from '../../../services/users/users.service';

interface IPath extends nameCode {}
interface ISchoolNameCode extends nameCode {}

@Component({
  selector: 'app-tramites',
  imports: [
    MessageModule,
    TableModule,
    CardModule,
    IconFieldModule,
    InputIconModule,
    InputTextModule,
    BarcodeReader,
    FormsModule,
    BadgeModule,
    StepperModule,
    CommonModule,
    ButtonModule,
    TagModule,
    ReactiveFormsModule,
    SelectModule,
    FloatLabel,
    ToastModule,
    TooltipModule,
  ],
  providers: [MessageService],
  standalone: true,
  templateUrl: './tramites.html',
  styleUrl: './tramites.scss',
})
export class Tramites {
  inventario: IInventaryItem[] = [];
  private $destroy = new Subject<void>();
  seletectedItems: IInventaryItem[] = [];
  metaKey: boolean = false;
  globalQuery: string = '';
  @ViewChild('dt') dt!: Table;
  activeStep: number = 1;

  paths!: IPath[];
  selectedPath: IPath | null = null;

  /* Prestamos de equipos */
  users: UserFromBackend[] = [];
  selectedUser: UserFromBackend | null = null;
  selectedSchool: ISchool | null = null;
  inventaryToLoan: IInventaryLoanInventary[] = [];
  projectName: string = '';
  justification: string = '';
  /* ------------------------------ */

  /* Dar de baja */
  inventaryToWriteOff: IInventaryWriteOff[] = [];
  /* ------------------------------ */

  constructor(
    private inventaryServices: InventaryService,
    private messageService: MessageService,
    private formalitiesService: FormalitiesService,
    private userService: UsersService,
  ) {}
  ngOnInit() {
    this.paths = [
      { name: 'Dar de baja', code: 'DB' },
      { name: 'Préstamo de equipos', code: 'PE' },
    ];
    this.inventaryServices.inventary$
      .pipe(
        takeUntil(this.$destroy),
        switchMap((data) => {
          if (data.length === 0) {
            return this.inventaryServices.getInventary().pipe(
              tap((data) => {
                this.inventaryServices.inventary = data;
              }),
            );
          }
          return of(data);
        }),
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

  getBarcodeNumber(message: string) {
    this.globalQuery = message;
    this.dt.filterGlobal(message, 'contains');
  }

  onImageError(event: any) {
    event.target.src = 'http://localhost:8000/media/inventario_images/noimage.webp';
  }

  getSeverity(item: IInventaryItem) {
    const inventoried = item.inventoried;
    return inventoried ? 'success' : 'danger';
  }

  getData() {
    this.getInventoryToWriteOff();
    this.getInventoryToLoan();
  }

  private getInventoryToWriteOff() {
    this.inventaryToWriteOff = this.seletectedItems.map((item) => ({
      inventario: item.inventario,
      motivo: '',
    }));
  }

  private getInventoryToLoan() {
    this.inventaryToLoan = this.seletectedItems.map((item) => ({
      inventario: item.inventario,
    }));
  }

  pathSelected() {
    if (this.selectedPath?.code === 'PE') {
      this.userService.users$
        .pipe(
          takeUntil(this.$destroy),
          switchMap((data) => {
            if (data.length === 0) {
              return this.userService.getUsers();
            }
            return of(data);
          }),
        )
        .subscribe({
          next: (response: UserFromBackend[] | any) => {
            console.log(response);
            this.users = response.map((user: UserFromBackend) => ({
              name: user.nombre,
              code: user.codigo,
              escuela: user.escuela,
              nombre: user.nombre,
            }));
          },
        });
    }
  }

  userSelected(selectedUser: UserFromBackend) {
    this.selectedSchool = selectedUser?.escuela || null;
  }

  updateValue(inventario: string, value: string) {
    const itemExistente = this.inventaryToWriteOff?.find((item) => item.inventario === inventario);
    if (itemExistente) {
      itemExistente.motivo = value;
    } else {
      this.inventaryToWriteOff?.push({ inventario, motivo: value });
    }
  }

  confirmTramite() {
    if (this.selectedPath?.code === 'DB') {
      if (this.inventaryToWriteOff.some((item) => item.motivo === '')) {
        this.errorMessage('El motivo de baja no puede estar vacio');
      } else {
        this.doTramite(this.inventaryToWriteOff, 'solicitud_baja');
      }
    } else if (this.selectedPath?.code === 'PE') {
      if (
        !this.selectedUser ||
        !this.selectedSchool ||
        this.projectName === '' ||
        this.justification === ''
      ) {
        this.errorMessage('Debe completar todos los campos del préstamo');
        return;
      } else {
        const loanRequest: IInventaryLoan = {
          fecha_devolucion: new Date().toISOString().split('T')[0],
          nombre_solicitante: this.selectedUser!.nombre,
          unidad_entidad: this.selectedSchool!.nombre,
          nombre_proyecto: this.projectName,
          justificacion: this.justification,
          items: this.inventaryToLoan,
        };
        console.log(loanRequest);
        this.doTramite(loanRequest, 'registrar_prestamo');
      }
    }
  }

  private doTramite(items: IInventaryWriteOff[] | IInventaryLoan, tramite: string) {
    this.formalitiesService.tramite(items, tramite).subscribe({
      next: (blob: Blob) => {
        downLoadExcel(blob);
        this.selectedPath = null;
        this.seletectedItems = [];
        this.inventaryToWriteOff = [];
        this.activeStep = 1;
      },
      error: (err) => {
        this.errorMessage('Error al generar el archivo Excel');
      },
    });
  }

  errorMessage(message: string) {
    this.messageService.add({
      severity: 'error',
      summary: 'Error',
      detail: message,
    });
  }

  ngOnDestroy() {
    this.$destroy.next();
    this.$destroy.complete();
  }
}
