import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  BehaviorSubject,
  catchError,
  Observable,
  of,
  shareReplay,
  take,
  tap,
  throwError,
} from 'rxjs';
import { IInventaryItem } from '../../models/inventary.model';

const url = 'https://2z4cjldp-8000.use2.devtunnels.ms';

@Injectable({
  providedIn: 'root',
})
export class InventaryService {
  private _httpClient = inject(HttpClient);
  private _inventary = new BehaviorSubject<IInventaryItem[]>([]);

  get inventary$(): Observable<IInventaryItem[]> {
    return this._inventary.asObservable();
  }

  getInventary(): Observable<IInventaryItem[]> {
    return this._httpClient.get(`${url}/api/dataImport/inventario-usuario/`).pipe(
      tap((response: any) => {
        this._inventary.next(response.items);
      }),
      catchError((error: any) => {
        this._inventary.next([]);
        return throwError(() => error);
      })
    );
  }

  uploadFile(file: File, Category: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('categoria', Category);
    return this._httpClient.post(`${url}/api/dataImport/importar-inventario/`, formData);
  }
}
