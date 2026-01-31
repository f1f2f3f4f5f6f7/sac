import { Routes } from '@angular/router';
import { hasRole } from './core/auth/guards/has-role-guard';
import { redirectByRoleGuard } from './core/auth/guards/redirect-by-role-guard';
import { authGuard } from './core/auth/guards/auth-guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canActivate: [redirectByRoleGuard],
    children: [],
  },
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
          import('./core/components/pages/manejoUsuarios/manejoUsuarios').then(
            (m) => m.ManejoUsuariosComponent,
          ),
      },
      {
        path: 'configuracion',
        loadComponent: () =>
          import('./core/components/pages/configuracionUsuario/configuracionUsuario').then(
            (m) => m.ConfiguracionUsuarioComponent,
          ),
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
          import('./core/components/pages/configuracionUsuario/configuracionUsuario').then(
            (m) => m.ConfiguracionUsuarioComponent,
          ),
      },
      {
        path: 'tramites',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./core/components/pages/tramites/tramites').then((m) => m.Tramites),
      },
    ],
  },
];
