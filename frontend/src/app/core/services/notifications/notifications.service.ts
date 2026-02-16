import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, map, Observable, throwError } from 'rxjs';

const url = 'http://localhost:8000/api/movimientos';

@Injectable({
  providedIn: 'root',
})
export class NotificationsService {
  private _httpClient = inject(HttpClient);
  getNotificactions(): Observable<any> {
    return this._httpClient.get(`${url}/listar_notificaciones/`).pipe(
      map((response: any) => {
        return response.resultados;
      }),
      catchError((error: any) => {
        return throwError(() => error);
      }),
    );
  }
}
