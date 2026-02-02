import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { IInventaryLoan, IInventaryWriteOff, IInvetaryTransfer } from '../../models/inventary.model';
import { catchError, Observable, throwError } from 'rxjs';

const url = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class FormalitiesService {
  private _httpClient = inject(HttpClient);

  tramite(items: IInventaryWriteOff | IInventaryLoan | IInvetaryTransfer, request: string) {
    const endpoint = `${url}/api/movimientos/${request}/`;

    return this._httpClient.post(endpoint,  items , {responseType: 'blob'}).pipe(
      catchError((error) => {
        return new Observable<never>((subscriber) => {
          error.error.text().then((errorMessage: string) => {
            subscriber.error(JSON.parse(errorMessage));
          });
        });
      }),
    )
  }
}
