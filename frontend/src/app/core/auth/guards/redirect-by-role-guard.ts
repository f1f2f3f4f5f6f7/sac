// core/auth/redirect-by-role.guard.ts
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';
import { RoleType } from '../../models/role.enum';

export const redirectByRoleGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const role = authService.role as RoleType;

  if (role === 'director') {
    return router.createUrlTree(['/director']);
  } else if (role === 'profesor') {
    return router.createUrlTree(['/profesor']);
  }

  // Si no hay rol o no está logueado, al login
  return router.createUrlTree(['/login']);
};