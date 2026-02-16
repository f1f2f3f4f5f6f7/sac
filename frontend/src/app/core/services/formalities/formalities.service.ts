import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  IInventaryLoan,
  IInventaryWriteOff,
  IInvetaryTransfer,
} from '../../models/inventary.model';
import { BehaviorSubject, catchError, map, Observable, throwError } from 'rxjs';

const url = 'http://localhost:8000/api/movimientos';

@Injectable({
  providedIn: 'root',
})
export class FormalitiesService {
  private _httpClient = inject(HttpClient);
  private _tramitePending = new BehaviorSubject<any[]>([]);

  get tramitesPending$(): Observable<any[]> {
    return this._tramitePending.asObservable();
  }

  set tramitesPending(items: any[]) {
    this._tramitePending.next(items);
  }

  tramite(items: IInventaryWriteOff | IInventaryLoan | IInvetaryTransfer, request: string) {
    const endpoint = `${url}/${request}/`;

    return this._httpClient.post(endpoint, items, { responseType: 'blob' }).pipe(
      catchError((error) => {
        return new Observable<never>((subscriber) => {
          error.error.text().then((errorMessage: string) => {
            subscriber.error(JSON.parse(errorMessage));
          });
        });
      }),
    );
  }

  getTramitePending() {
    return this._httpClient
      .get(`${url}/consultar_trazabilidad/`, {
        params: {
          estado: 'pendiente',
        },
      })
      .pipe(
        map((response: any) => {
          this.tramitesPending = response.resultados;
          return response.resultados;
        }),
        catchError((error) => throwError(() => error.error)),
      );
  }

  confirmTramitePending(file: any, body: any) {
    const formData = new FormData();
    formData.append('archivo', body.archivo);
    formData.append('accion', body.accion);
    formData.append('archivo_firmado', file);
    return this._httpClient.post(`${url}/${body.tramite}/`, formData).pipe(
      catchError((error) => {
        return throwError(() => error.error);
      }),
    );
  }
}
