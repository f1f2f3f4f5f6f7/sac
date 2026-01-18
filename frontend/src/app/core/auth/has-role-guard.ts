import { inject } from '@angular/core';
import { map, tap } from 'rxjs';
import { AuthService } from './auth.service';
import { RoleType } from '../models/role.enum';

export function hasRole(allowedRoles: RoleType[]) {
  return () =>
    inject(AuthService).user$.pipe(
      map((user) => Boolean(user && allowedRoles.includes(user.rol))),
      tap((hasRole) => hasRole === false && alert('Acceso Denegado'))
    );
}