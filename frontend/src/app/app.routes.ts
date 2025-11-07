import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth-guard';
import { hasRole } from './core/auth/has-role-guard';
import { inject } from '@angular/core';
import { InventaryService } from './core/services/inventary/inventary.service';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./core/components/pages/login/login').then((m) => m.Login),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/component/app.layout').then((m) => m.AppLayout),
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./core/components/pages/dashboard/dashboard').then((m) => m.Dashboard),
        resolve: {
          inventary: () => inject(InventaryService).getInventary()
        }
      },
    {
      path: 'rendicion',
      canActivate: [authGuard],
      loadComponent: () => import('./core/components/pages/rendicion/rendicion').then((m) => m.Rendicion)
    }
    ],
  },
];
