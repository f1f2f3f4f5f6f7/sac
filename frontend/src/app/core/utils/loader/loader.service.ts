import { computed, Injectable, signal } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoaderService {
  #showLoader = signal<boolean>(false);
  showLoader = computed(() => this.#showLoader());
  loaderSubject: any;

  constructor() { }

  show() {
    this.#showLoader.set(true);
  }
  hide() {
    this.#showLoader.set(false);
  }
}
