import { inject } from '@angular/core';
import { map, tap } from 'rxjs';
import { AuthService } from './auth.service';
import { RoleType } from '../models/role.enum';

export function hasRole(allowedRoles: RoleType[]) {
  return () =>
    allowedRoles.includes(inject(AuthService).role as RoleType) ? true : alert('Access Denied: You do not have the required role to access this page.');
}