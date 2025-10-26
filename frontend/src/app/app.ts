import { Component, inject, signal } from '@angular/core';
import { NavigationError, Router, RouterOutlet } from '@angular/router';
import { Loader } from './core/utils/loader/loader/loader';
import { filter, map } from 'rxjs';
import { Button } from 'primeng/button';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Loader, Button],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly title = signal('frontend');
  private router = inject(Router);
  private lastFailedUrl = signal('');
  protected errorMessage = signal<string>('');

  constructor() {
    this.router.events
      .pipe(filter((e): e is NavigationError => e instanceof NavigationError))
      .subscribe((e) => {
        this.lastFailedUrl.set(e.url);
        this.errorMessage.set('Ha ocurrido un error en la petición');
      });
  }

  retryNavigation() {
    if (this.lastFailedUrl()) {
      this.errorMessage.set('');
      this.router.navigateByUrl(this.lastFailedUrl());
    }
  }
}
