import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { RippleModule } from 'primeng/ripple';
import { InputTextModule } from 'primeng/inputtext';
import { CheckboxModule } from 'primeng/checkbox';
import { PasswordModule } from 'primeng/password';
import { catchError, EMPTY, shareReplay } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { AppFloatingConfigurator } from '../../../../layout/component/app.floatingconfigurator';
import { AuthService } from '../../../auth/auth.service';
import { UserLogin } from '../../../models/user.model';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ButtonModule,
    CheckboxModule,
    InputTextModule,
    PasswordModule,
    FormsModule,
    RouterModule,
    RippleModule,
    AppFloatingConfigurator,
    ToastModule
  ],
  templateUrl: './login.html',
  styleUrl: './login.scss',
  providers: [MessageService]
})
export class Login {
  codigo: string = '';

  password: string = '';

  checked: boolean = false;

  constructor(public authService: AuthService, public messageService: MessageService) {}

  login(){
    const userLogin: UserLogin = {
      codigo: this.codigo,
      password: this.password
    }
    this.authService.login(userLogin).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          this.messageService.add({ severity: 'error', summary: 'Fallido', detail: error?.error.error || 'Error de autenticación' });
        }
        return EMPTY
      }),
    ).subscribe()
  }
}
