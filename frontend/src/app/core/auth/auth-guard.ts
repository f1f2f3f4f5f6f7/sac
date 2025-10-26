import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const router = inject(Router);
  return inject(AuthService).islogged$.pipe(
    map(isLogged => isLogged ? true : router.createUrlTree(['/login']))
  );
};