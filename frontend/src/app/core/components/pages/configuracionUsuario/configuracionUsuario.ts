import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { AuthService } from '../../../auth/auth.service';
import { UsersService } from '../../../services/users/users.service';
import { Subject, takeUntil, take } from 'rxjs';

@Component({
  selector: 'app-configuracion-usuario',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ToastModule,
    ButtonModule,
    InputTextModule
  ],
  templateUrl: './configuracionUsuario.html',
  styleUrls: ['./configuracionUsuario.scss'],
  providers: [MessageService]
})
export class ConfiguracionUsuarioComponent implements OnInit, OnDestroy {
  email = '';
  originalEmail = ''; // Guardar email original para comparar
  password = {
    current: '',
    new: '',
    confirm: ''
  };

  saving = false;
  private destroy$ = new Subject<void>();
  private userCodigo = '';

  constructor(
    private messageService: MessageService,
    private authService: AuthService,
    private usersService: UsersService
  ) {}

  ngOnInit() {
    this.loadUserProfile();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadUserProfile() {
    this.authService.user$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => {
        if (user) {
          this.email = user.email || '';
          this.originalEmail = user.email || ''; // Guardar email original
          this.userCodigo = user.codigo || '';
        }
      });
  }

  save() {
    // Verificar si hay cambios
    const emailChanged = this.email !== this.originalEmail;
    const passwordChanged = this.password.new && this.password.new.length > 0;

    // Validar que al menos haya un cambio
    if (!emailChanged && !passwordChanged) {
      this.messageService.add({
        severity: 'info',
        summary: 'Sin cambios',
        detail: 'No hay cambios para guardar'
      });
      return;
    }

    // Validar email si cambió
    if (emailChanged) {
      if (!this.email || !this.email.trim()) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Campo incompleto',
          detail: 'El email es requerido'
        });
        return;
      }
    }

    // Validar contraseñas si se están cambiando
    if (passwordChanged) {
      // Validar que se haya ingresado la contraseña actual
      if (!this.password.current) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Campo incompleto',
          detail: 'Debe ingresar su contraseña actual'
        });
        return;
      }

      if (!this.password.new || !this.password.confirm) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Campos incompletos',
          detail: 'Complete todos los campos de contraseña'
        });
        return;
      }

      if (this.password.new !== this.password.confirm) {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Las contraseñas no coinciden'
        });
        return;
      }

      if (this.password.new.length < 6) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Contraseña inválida',
          detail: 'La contraseña debe tener al menos 6 caracteres'
        });
        return;
      }
    }

    this.saving = true;

    // Preparar datos de actualización según lo que cambió
    const updateData: any = {
      codigo: this.userCodigo
    };

    // Agregar email solo si cambió
    if (emailChanged) {
      updateData.email = this.email.toLowerCase().trim();
    }

    // Agregar password y current_password si se está cambiando
    if (passwordChanged) {
      updateData.password = this.password.new;
      updateData.current_password = this.password.current; // Enviar contraseña actual para validación
    }

    // Llamar al servicio que ya está conectado con update_user_view
    this.usersService.updateUser(updateData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            this.messageService.add({
              severity: 'success',
              summary: 'Cambios guardados',
              detail: response.message || 'Los cambios fueron guardados correctamente'
            });
            
            // Actualizar el usuario en el servicio de autenticación
            // Usar take(1) para evitar suscripciones infinitas
            this.authService.user$
              .pipe(take(1), takeUntil(this.destroy$))
              .subscribe(user => {
                if (user) {
                  this.authService.userLogged({
                    ...user,
                    email: response.user.email
                  });
                  // Actualizar el email original para futuras comparaciones
                  this.originalEmail = response.user.email;
                }
              });

            // Limpiar campos de contraseña si se actualizó
            if (passwordChanged) {
              this.password = { current: '', new: '', confirm: '' };
            }
          }
          this.saving = false;
        },
        error: (error) => {
          console.error('Error al guardar cambios:', error);
          const errorMessage = error?.error?.error || 'Error al guardar los cambios';
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: errorMessage
          });
          this.saving = false;
        }
      });
  }
}