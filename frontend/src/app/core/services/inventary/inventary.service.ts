import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs/operators';
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
import { IBusquedaGeneralResult } from '../../models/inventary.model';

const url = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class InventaryService {
  private _httpClient = inject(HttpClient);
  private _inventary = new BehaviorSubject<IInventaryItem[]>([]);

  get inventary$(): Observable<IInventaryItem[]> {
    return this._inventary.asObservable();
  }

  set inventary(items: IInventaryItem[]) {
    this._inventary.next(items);
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


    // Nuevo método para búsqueda generalizada
    buscarInventarioGeneral(inventarioNumero: string): Observable<IBusquedaGeneralResult> {
      return this._httpClient.get<{success: boolean, item: IBusquedaGeneralResult, message?: string}>(
        `${url}/api/busquedaGeneral/buscar/`,
        { params: { inventario: inventarioNumero } }
      ).pipe(
        tap((response) => {
          if (!response.success) {
            throw new Error(response.message || 'No se encontró el inventario');
          }
        }),
        // Usar map para transformar la respuesta
        map((response) => response.item),
        catchError((error: any) => {
          return throwError(() => error);
        })
      );
    }
}
