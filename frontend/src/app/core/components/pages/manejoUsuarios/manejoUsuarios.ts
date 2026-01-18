import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConfirmationService, MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { CardModule } from 'primeng/card';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { UsersService, UserFromBackend } from '../../../services/users/users.service';
import { Subject, takeUntil } from 'rxjs';
import { PasswordModule } from 'primeng/password';
import { Table } from 'primeng/table';



interface User {
    id: number;
    codigo: string;
    name: string;
    email: string;
    role: string;
    escuela: {
      id: number;
      nombre: string;
    } | null;
  }

  interface NewUserForm {
    codigo: string;
    nombre: string;
    email: string;
    password: string;
  }


@Component({
  selector: 'app-manejoUsuarios',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    SelectModule,
    TagModule,
    PasswordModule,
    ToastModule,
    ConfirmDialogModule,
    CardModule,
    IconFieldModule,
    InputIconModule,
    ProgressSpinnerModule
  ],
  templateUrl: './manejoUsuarios.html',
  styleUrls: ['./manejoUsuarios.scss'],
  providers: [ConfirmationService, MessageService]
})
export class ManejoUsuariosComponent implements OnInit, OnDestroy {
  @ViewChild('dv') dv!: Table;
  userDialog = false;
  users: User[] = [];
  loading = false;
  saving = false;
  globalQuery: string = '';
  private destroy$ = new Subject<void>();

  newUser: NewUserForm = { codigo: '', nombre: '', email: '', password: '' };

  constructor(
    private confirmService: ConfirmationService,
    private messageService: MessageService,
    private usersService: UsersService
  ) {}

  ngOnInit() {
    this.loadUsers();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadUsers() {
    this.loading = true;
    this.usersService.getUsers()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            // Mapear los datos del backend a la estructura del componente
            this.users = response.users.map(user => ({
              id: user.id,
              codigo: user.codigo,
              name: user.nombre,
              email: user.email,
              role: user.rol,
              escuela: user.escuela
            }));
          }
          this.loading = false;
        },
        error: (error) => {
          console.error('Error al cargar usuarios:', error);
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudieron cargar los usuarios'
          });
          this.loading = false;
        }
      });
  }

  openNew() {
    this.newUser = { codigo: '', nombre: '', email: '', password: '' };
    this.userDialog = true;
  }

  saveUser() {
    // Validar campos requeridos
    if (!this.newUser.codigo || !this.newUser.nombre || !this.newUser.email || !this.newUser.password) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Campos incompletos',
        detail: 'Por favor complete todos los campos'
      });
      return;
    }

    // Validar longitud de contraseña
    if (this.newUser.password.length < 6) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Contraseña inválida',
        detail: 'La contraseña debe tener al menos 6 caracteres'
      });
      return;
    }

    this.saving = true;
    
    const userData = {
      codigo: this.newUser.codigo.toUpperCase(),
      nombre: this.newUser.nombre,
      email: this.newUser.email.toLowerCase(),
      password: this.newUser.password,
      rol: 'profesor',
      escuela_id: 5
    };

    this.usersService.registerUser(userData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            this.messageService.add({
              severity: 'success',
              summary: 'Usuario creado',
              detail: 'El usuario fue agregado correctamente'
            });
            this.userDialog = false;
            this.loadUsers(); // Recargar la lista de usuarios
          }
          this.saving = false;
        },
        error: (error) => {
          console.error('Error al crear usuario:', error);
          const errorMessage = error?.error?.error || 'Error al crear el usuario';
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: errorMessage
          });
          this.saving = false;
        }
      });
  }

  deleteUser(user: User) {
    this.confirmService.confirm({
      message: `¿Está seguro que desea eliminar al usuario ${user.name} (${user.codigo})?`,
      header: 'Confirmar eliminación',
      icon: 'pi pi-exclamation-triangle',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        this.usersService.deleteUser(user.codigo)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: (response) => {
              if (response.success) {
                this.messageService.add({
                  severity: 'success',
                  summary: 'Eliminado',
                  detail: response.message || 'Usuario eliminado correctamente'
                });
                this.loadUsers(); // Recargar la lista de usuarios
              }
            },
            error: (error) => {
              console.error('Error al eliminar usuario:', error);
              const errorMessage = error?.error?.error || 'Error al eliminar el usuario';
              this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: errorMessage
              });
            }
          });
      }
    });
  }
}