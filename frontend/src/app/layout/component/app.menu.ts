import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MenuItem } from 'primeng/api';
import { AppMenuitem } from './app.menuitem';
import { AuthService } from '../../core/auth/auth.service';
import { map } from 'rxjs';

@Component({
  selector: 'app-menu',
  standalone: true,
  imports: [CommonModule, AppMenuitem, RouterModule],
  template: `<ul class="layout-menu">
    <ng-container *ngFor="let item of model; let i = index">
      <li app-menuitem *ngIf="!item.separator" [item]="item" [index]="i" [root]="true"></li>
      <li *ngIf="item.separator" class="menu-separator"></li>
    </ng-container>
  </ul> `,
})
export class AppMenu implements OnInit {
  model: MenuItem[] = [];

  constructor(private authService: AuthService) {}

  ngOnInit() {
    if (this.authService.role === 'director') {
      this.model = [
        {
          label: 'Home',
          items: [{ label: 'Usuarios', icon: 'pi pi-fw pi-users', routerLink: ['/director'] }],
        },
        {
          label: 'Movimientos',
          items: [
            {
              label: 'Tramites',
              icon: 'pi pi-fw pi-arrow-right-arrow-left',
              routerLink: ['/director/tramites'],
            },
            {
              label: 'Tramites Pendientes',
              icon: 'pi pi-fw pi-clock',
              routerLink: ['/director/tramites-pendientes'],
            },
            {
              label: 'Notificaciones',
              icon: 'pi pi-fw pi-bell',
              routerLink: ['/director/notificaciones'],
            },
          ],
        },
        {
          label: 'Registros',
          items: [
            {
              label: 'Trazabilidad',
              icon: 'pi pi-fw pi-history',
              routerLink: ['/director/trazabilidad'],
            },
          ],
        },
      ];
    } else {
      this.model = [
        {
          label: 'Home',
          items: [{ label: 'Dashboard', icon: 'pi pi-fw pi-home', routerLink: ['/profesor'] }],
        },
        {
          label: 'Actividades',
          items: [
            {
              label: 'Rendición de Inventarío',
              icon: 'pi pi-fw pi-id-card',
              routerLink: ['/profesor/rendicion'],
            },
            {
              label: 'Busqueda General',
              icon: 'pi pi-fw pi-search',
              routerLink: ['/profesor/busqueda'],
            },
          ],
        },
        {
          label: 'Movimientos',
          items: [
            {
              label: 'Tramites',
              icon: 'pi pi-fw pi-arrow-right-arrow-left',
              routerLink: ['/profesor/tramites'],
            },
            {
              label: 'Tramites Pendientes',
              icon: 'pi pi-fw pi-clock',
              routerLink: ['/profesor/tramites-pendientes'],
            },
            {
              label: 'Notificaciones',
              icon: 'pi pi-fw pi-bell',
              routerLink: ['/profesor/notificaciones'],
            },
          ],
        },
        {
          label: 'Registros',
          items: [
            {
              label: 'Trazabilidad',
              icon: 'pi pi-fw pi-history',
              routerLink: ['/profesor/trazabilidad'],
            },
          ],
        },
      ];
    }

    /*             {
                label: 'Pages',
                icon: 'pi pi-fw pi-briefcase',
                routerLink: ['/pages'],
                items: [
                    {
                        label: 'Landing',
                        icon: 'pi pi-fw pi-globe',
                        routerLink: ['/landing']
                    },
                    {
                        label: 'Auth',
                        icon: 'pi pi-fw pi-user',
                        items: [
                            {
                                label: 'Login',
                                icon: 'pi pi-fw pi-sign-in',
                                routerLink: ['/auth/login']
                            },
                            {
                                label: 'Error',
                                icon: 'pi pi-fw pi-times-circle',
                                routerLink: ['/auth/error']
                            },
                            {
                                label: 'Access Denied',
                                icon: 'pi pi-fw pi-lock',
                                routerLink: ['/auth/access']
                            }
                        ]
                    },
                    {
                        label: 'Crud',
                        icon: 'pi pi-fw pi-pencil',
                        routerLink: ['/pages/crud']
                    },
                    {
                        label: 'Not Found',
                        icon: 'pi pi-fw pi-exclamation-circle',
                        routerLink: ['/pages/notfound']
                    },
                    {
                        label: 'Empty',
                        icon: 'pi pi-fw pi-circle-off',
                        routerLink: ['/pages/empty']
                    }
                ]
            },
            {
                label: 'Hierarchy',
                items: [
                    {
                        label: 'Submenu 1',
                        icon: 'pi pi-fw pi-bookmark',
                        items: [
                            {
                                label: 'Submenu 1.1',
                                icon: 'pi pi-fw pi-bookmark',
                                items: [
                                    { label: 'Submenu 1.1.1', icon: 'pi pi-fw pi-bookmark' },
                                    { label: 'Submenu 1.1.2', icon: 'pi pi-fw pi-bookmark' },
                                    { label: 'Submenu 1.1.3', icon: 'pi pi-fw pi-bookmark' }
                                ]
                            },
                            {
                                label: 'Submenu 1.2',
                                icon: 'pi pi-fw pi-bookmark',
                                items: [{ label: 'Submenu 1.2.1', icon: 'pi pi-fw pi-bookmark' }]
                            }
                        ]
                    },
                    {
                        label: 'Submenu 2',
                        icon: 'pi pi-fw pi-bookmark',
                        items: [
                            {
                                label: 'Submenu 2.1',
                                icon: 'pi pi-fw pi-bookmark',
                                items: [
                                    { label: 'Submenu 2.1.1', icon: 'pi pi-fw pi-bookmark' },
                                    { label: 'Submenu 2.1.2', icon: 'pi pi-fw pi-bookmark' }
                                ]
                            },
                            {
                                label: 'Submenu 2.2',
                                icon: 'pi pi-fw pi-bookmark',
                                items: [{ label: 'Submenu 2.2.1', icon: 'pi pi-fw pi-bookmark' }]
                            }
                        ]
                    }
                ]
            },
            {
                label: 'Get Started',
                items: [
                    {
                        label: 'Documentation',
                        icon: 'pi pi-fw pi-book',
                        routerLink: ['/documentation']
                    },
                    {
                        label: 'View Source',
                        icon: 'pi pi-fw pi-github',
                        url: 'https://github.com/primefaces/sakai-ng',
                        target: '_blank'
                    }
                ]
            } */
  }
}
