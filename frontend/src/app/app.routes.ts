import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth-guard';
import { hasRole } from './core/auth/has-role-guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./core/components/pages/login/login').then((m) => m.Login),
  },
  {
    path: 'director',
    canActivate: [authGuard, hasRole(['director'])],
    loadComponent: () => import('./layout/component/app.layout').then((m) => m.AppLayout),
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./core/components/pages/manejoUsuarios/manejoUsuarios').then((m) => m.ManejoUsuariosComponent),
      },
      {
        path: 'configuracion',
        loadComponent: () =>
          import('./core/components/pages/configuracionUsuario/configuracionUsuario').then((m) => m.ConfiguracionUsuarioComponent),
      },
    ],
  },
  {
    path: 'profesor',
    canActivate: [authGuard, hasRole(['profesor'])],
    loadComponent: () => import('./layout/component/app.layout').then((m) => m.AppLayout),
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./core/components/pages/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'rendicion',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./core/components/pages/rendicion/rendicion').then((m) => m.Rendicion),
      },
      {
        path: 'busqueda',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./core/components/pages/busqueda/busqueda').then((m) => m.Busqueda),
      },
      {
        path: 'configuracion',
        loadComponent: () =>
          import('./core/components/pages/configuracionUsuario/configuracionUsuario').then((m) => m.ConfiguracionUsuarioComponent),
      },
    ],
  },
];