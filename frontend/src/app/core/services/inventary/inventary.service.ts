import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, catchError, Observable, of, shareReplay, take, tap, throwError } from 'rxjs';
import { IInventaryItem } from '../../models/inventary.model';

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
    return this._httpClient.get('http://localhost:8000/api/dataImport/inventario-usuario/').pipe(
      tap((response: any) => {
        this._inventary.next(response.items);
      }),
      catchError((error: any) => {
        this._inventary.next([]);
        return throwError(() => error);
      })
    );
  }

  uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this._httpClient.post(
      'http://localhost:8000/api/dataImport/importar-inventario/',
      formData
    );
  }
}
