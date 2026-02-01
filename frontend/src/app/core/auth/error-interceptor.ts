import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const authService = inject(AuthService);
  return next(req).pipe(
    catchError((error) => {
      // Si recibimos 401, el token es inválido
      if (error.status === 401) {
        console.error('🔒 401 Unauthorized - Token inválido');
        // Limpiar token
        localStorage.removeItem('accessToken');
        localStorage.removeItem('role');
        authService.userLogged(null);
        // Redirigir al login
        router.navigateByUrl('/login');
      }
      return throwError(() => error);
    })
  );
};
